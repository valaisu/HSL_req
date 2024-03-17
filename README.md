# HSL_req
Request data with HSL api

If you want to set this up for your self, you also need to create "secret_data.py".
This file shoud contain some key variables like

TOKEN1:     Access token for the api, see https://digitransit.fi/en/developers/api-registration/
STOPS:      List of the IDs of the transport stops you want timetables from

if you want to use the itinerary (= route from a to b) feature, also add some locations like 
HOME:       Tuple of lat and lon coordinates
