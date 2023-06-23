def has_footprint_intersection(open_acquisition1, open_acquisition2, delta_time):
    times1 = (open_acquisition1.start_date - delta_time, open_acquisition1.stop_date + delta_time)
    times2 = (open_acquisition2.start_date - delta_time, open_acquisition2.stop_date + delta_time)
    if times1[1] < times2[0] or times2[1] < times1[0]:
        return False  # No time match => no footprint
    else:
        start_date = max(times1[0], times2[0])
        stop_date = min(times1[1], times2[1])
    if (open_acquisition1.acquisition_type == 'truncated_swath') \
            and (open_acquisition2.acquisition_type == 'truncated_swath'):
        return open_acquisition1.footprint\
            .intersects(open_acquisition2.footprint)

def intersection_drg_truncated_swath(open_acquisition1, open_acquisition2, delta_time):

