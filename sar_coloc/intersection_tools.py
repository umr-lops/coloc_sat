def extract_times_dataset(open_acquisition, time_name='time', dataset=None, start_date=None, stop_date=None):
    """
    Extract a sub-dataset from a dataset of an acquisition to get a time dataset within 2 bounds (dates). If one of
    th bound exceeds the acquisition extremum times, so the acquisition Start and/ or Stop dates are chosen.

    Parameters
    ----------
    open_acquisition: open_smos.OpenSmos | open_hy.OpenHy | open_era.OpenEra
        Open object from an acquisition
    time_name: str
        name of the time variable in the ds
    dataset: xarray.Dataset | None
        dataset on which we want to extract some values depending on times. If it is None, extraction is made on
        `open_acquisition.dataset`; else extraction is made on the specified dataset
    start_date: numpy.datetime64 | None
        Start chosen date.
    stop_date: numpy.datetime64 | None
        End chosen date.

    Returns
    -------
    xarray.Dataset | None
        Contains a sub-dataset of the acquisition dataset (between `start_date` and `stop_date`).
    """
    if dataset is None:
        dataset = open_acquisition.dataset
    if dataset is None:
        return dataset
    if start_date is None:
        start_date = open_acquisition.start_date
    if stop_date is None:
        stop_date = open_acquisition.stop_date
    return dataset.where((dataset[time_name] >= start_date) &
                         (dataset[time_name] <= stop_date), drop=True)


def are_dimensions_empty(dataset):
    """
    Verify if a dataset has all its dimensions empty

    Parameters
    ----------
    dataset: xarray.Dataset
        dataset on which empty verification needs to be done

    Returns
    -------
    bool
        True if dataset has all its dimensions empty
    """
    for dimension in dataset.dims:
        if len(dataset[dimension]) != 0:
            return False  # One dimension isn't empty => there are values
    return True
