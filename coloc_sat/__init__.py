"""Top-level package for coloc_sat."""

__author__ = """Yann Reynaud"""
__email__ = "yann.reynaud.2@ifremer.fr"
__all__ = [
    "GetSarMeta",
    "GetEra5Meta",
    "GetHy2Meta",
    "GetSmosMeta",
    "GetWindSatMeta",
    "GetSmapMeta",
    "ProductIntersection",
    "GenerateColoc",
]

from .version import __version__
from .sar_meta import GetSarMeta
from .era5_meta import GetEra5Meta
from .hy2_meta import GetHy2Meta
from .smos_meta import GetSmosMeta
from .windsat_meta import GetWindSatMeta
from .smap_meta import GetSmapMeta
from .intersection import ProductIntersection
from .generate_coloc import GenerateColoc
from . import *
import struct
import socket
import fcntl
import os


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(
        fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack("256s", str.encode(ifname[:15])),
        )[20:24]
    )


def init_cluster(n_workers: int, memory: int):
    from dask_jobqueue import PBSCluster
    from dask.distributed import Client

    # see https://jobqueue.dask.org/en/latest/generated/dask_jobqueue.PBSCluster.html
    memory = f"{memory}GB"
    nprocs = 1
    cluster = PBSCluster(
        cores=nprocs,
        memory=memory,
        project="wind_distribution",
        queue="sequentiel",
        processes=nprocs,
        resource_spec="select=1:ncpus=%d:mem=%s" % (nprocs, memory),
        local_directory=os.path.expandvars("$TMPDIR"),
        interface="ib1",  # workers interface (routable to queue ftp)
        walltime="00:20:00",
        scheduler_options={"interface": "ib0"},
        job_extra=["-m n"],
    )  # if scheduler is on queue 'ftp'

    cluster.scale(jobs=n_workers)  # ask for 200 jobs

    c = Client(cluster)
    # getting a working dashboard link is little tricky on datarmor
    print(
        "Client dashboard: %s"
        % c.dashboard_link.replace(get_ip_address("ib0"), get_ip_address("bond1"))
    )
    return c
