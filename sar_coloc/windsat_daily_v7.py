#	This routine reads version-7.0.1 RSS WindSat daily files 
#
# 	filename  name of data file with path in form satname_yyyymmdd_v7.0.1.gz
#	 where satname  = name of satellite (wsat)
#	       yyyy		= year
#		   mm		= month
#		   dd		= day of month
#   missing = fill value used for missing data;
#                  if None, then fill with byte codes (251-255)

##	the output values correspond to:
#	time		time of measurement in fractional hours GMT
#	sst			sea surface temperature in deg Celsius
#	windLF		10m surface wind, low frequency, in meters/second
#	windMF		10m surface wind, medium frequency, in meters/second
#	vapor		columnar or integrated water vapor in millimeters
#	cloud		cloud liquid water in millimeters
#	rain		rain rate in millimeters/hour
#   longitude	Grid Cell Center Longitude', LON = 0.25*x_grid_location - 0.125 degrees east
#   latitude	Grid Cell Center Latitude',  LAT = 0.25*y_grid_location - 90.125
#   land		Is this land?
#   ice			Is this ice?
#   nodata		Is there no data
#
#   if you need help with this python read code, contact support@remss.com


from .bytemaps import sys
from .bytemaps import Dataset
from .bytemaps import Verify
import xarray as xr


def to_xarray_dataset(raw):
    """
    Convert a WindSat dataset (format given by REMSS reader) to a xarray dataset.
    Parameters:
        raw (windsat_daily_v7.WindSatDaily): WindSat dataset in initial format.
    Returns
        (xarray.Dataset): WindSat dataset in xarray format.
    """

    def to_tuple(var):
        dims = var.coordinates
        data = var  # the Variable class is a subclass of ndarray
        attrs = {name: getattr(var, name) for name in raw._attributes() if name not in ["coordinates"]}
        return dims, data, attrs

    all_vars = {
        name: to_tuple(var)
        for name, var in raw.variables.items()
    }
    coordinate_names = raw._coordinates()
    data_vars = {k: v for k, v in all_vars.items() if k not in coordinate_names}
    coords = {k: v for k, v in all_vars.items() if k in coordinate_names}
    if "orbit_segment" not in coords:
        coords["orbit_segment"] = ("orbit_segment", ["descending", "ascending"])

    ds = xr.Dataset(coords=coords, data_vars=data_vars)
    ds.encoding["source"] = raw.filename

    return ds


class WindSatDaily(Dataset):
    """ Read daily WindSat bytemaps. """
    """
    Public data:
        filename = name of data file
        missing = fill value used for missing data;
                  if None, then fill with byte codes (251-255)
        dimensions = dictionary of dimensions for each coordinate
        variables = dictionary of data for each variable
    """

    def __init__(self, filename, missing=-999.):
        """
        Required arguments:
            filename = name of data file to be read (string)
                
        Optional arguments:
            missing = fill value for missing data,
                      default is the value used in verify file
        """
        self.filename = filename
        self.missing = missing
        Dataset.__init__(self)

    # Dataset:

    def _attributes(self):
        return ['coordinates','long_name','units','valid_min','valid_max']

    def _coordinates(self):
        return ('orbit_segment','variable','latitude','longitude')

    def _shape(self):
        return (2,9,720,1440)

    def _variables(self):
        return ['mingmt','sst','w-lf','w-mf','vapor','cloud','rain',
                'w-aw','wdir','longitude','latitude','land','ice','nodata']                

    # _default_get():
    
    def _get_index(self,var):
        return {'mingmt' : 0,
                'sst' : 1,
                'w-lf' : 2,
                'w-mf' : 3,
                'vapor' : 4,
                'cloud' : 5,
                'rain' : 6,
                'w-aw' : 7,
                'wdir' : 8,
                }[var]

    def _get_scale(self,var):
        return {'mingmt' : 6.0,
                'sst' : 0.15,
                'w-lf' : 0.2,
                'w-mf' : 0.2,
                'vapor' : 0.3,
                'cloud' : 0.01,
                'rain' : 0.1,
                'w-aw' : 0.2,
                'wdir' : 1.5,
                }[var]

    def _get_offset(self,var):
        return {'sst' : -3.0,
                'cloud' : -0.05,
                }[var]

    # _get_ attributes:

    def _get_long_name(self,var):
        return {'mingmt' : 'Time of Day UTC',
                'sst' : 'Sea Surface Temperature',
                'w-lf' : '10-m Surface Wind Speed (low frequency)',
                'w-mf' : '10-m Surface Wind Speed (medium frequency)',
                'vapor' : 'Columnar Water Vapor',
                'cloud' : 'Cloud Liquid Water',
                'rain' : 'Surface Rain Rate',
                'w-aw' : 'All-Weather 10-m Surface Wind Speed',
                'wdir' : 'Surface Wind Direction',
                'longitude' : 'Grid Cell Center Longitude',
                'latitude' : 'Grid Cell Center Latitude',
                'land' : 'Is this land?',
                'ice' : 'Is this ice?',
                'nodata' : 'Is there no data?',
                }[var]

    def _get_units(self,var):
        return {'mingmt' : 'Minutes since midnight GMT',
                'sst' : 'deg Celsius',
                'w-lf' : 'm/s',
                'w-mf' : 'm/s',
                'vapor' : 'mm',
                'cloud' : 'mm',
                'rain' : 'mm/hr',
                'w-aw' : 'm/s',
                'wdir' : 'deg oceanographic',
                'longitude' : 'degrees east',
                'latitude' : 'degrees north',
                'land' : 'True or False',
                'ice' : 'True or False',
                'nodata' : 'True or False',
                }[var]

    def _get_valid_min(self,var):
        return {'mingmt' : 0.0,
                'sst' : -3.0,
                'w-lf' : 0.0,
                'w-mf' : 0.0,
                'vapor' : 0.0,
                'cloud' : -0.05,
                'rain' : 0.0,
                'w-aw' : 0.2,
                'wdir' : 0.0,
                'longitude' : 0.0,
                'latitude' : -90.0,
                'land' : False,
                'ice' : False,
                'nodata' : False,
                }[var]

    def _get_valid_max(self,var):
        return {'mingmt' : 1440.0,
                'sst' : 34.5,
                'w-lf' : 50.0,
                'w-mf' : 50.0,
                'vapor' : 75.0,
                'cloud' : 2.45,
                'rain' : 25.0,
                'w-aw' : 50.0,
                'wdir' : 360.0,
                'longitude' : 360.0,
                'latitude' : 90.0,
                'land' : True,
                'ice' : True,
                'nodata' : True,
                }[var]


class DailyVerify(Verify):
    """ Contains info for verification. """
    
    def __init__(self,dataset):
        self.filename = 'windsat_V7_verify.txt'
        self.ilon1 = 170
        self.ilon2 = 175
        self.ilat1 = 274
        self.ilat2 = 278                
        self.iasc = 1
        self.variables = ['mingmt','sst','w-lf','w-mf','vapor',
                          'cloud','rain','w-aw','wdir']        
        self.startline = 97
        self.columns = {'mingmt' : 3,
                        'sst' : 4,
                        'w-lf' : 5,
                        'w-mf' : 6,
                        'vapor' : 7,
                        'cloud' : 8,
                        'rain' : 9,
                        'w-aw' : 10,
                        'wdir' : 11 }
        Verify.__init__(self,dataset)
        

if __name__ == '__main__':
    """ Automated testing. """

    # read daily:    
    wsat = WindSatDaily('wsat_20060409v7.0.1.gz')
    if not wsat.variables: sys.exit('file not found')
    
    # verify daily:
    verify = DailyVerify(wsat)
    if verify.success: print('successful verification for daily')
    else: sys.exit('verification failed for daily')
    print('')

    print('all tests completed successfully')
    print('')
