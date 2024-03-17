import requests
import json
from datetime import datetime
import time

from secret_info import TOKEN1, STOPS, HOME, UNI

"""
TOKEN1: str: access token
HOME, UNI: Tuple(float, float): coordinates of locations
STOPS: list[str]: HSL IDs of transport stops
"""

BASE_URL = "https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"


def arrival_predictions(stop_id: str, token: str = TOKEN1):
    """
    Requests data about a specific transport station 
    
    """
    graphql_query = f"""
    {{
        stop(id: "{stop_id}") {{
            name
            stoptimesWithoutPatterns {{
                scheduledArrival
                realtimeArrival
                realtime
                realtimeState
                headsign
                trip {{
                    route {{
                        shortName
                    }}
                }}
            }}
        }}
    }}
    """

    response = requests.post(
        url=BASE_URL,
        headers={"Content-Type": "application/json", "digitransit-subscription-key": token},
        data=json.dumps({"query": graphql_query})
    )
    response.raise_for_status()
    return response.json()


def find_routes(start_coord: tuple[float, float], end_coord: tuple[float, float], 
                day: str = datetime.today().strftime("%Y-%m-%d"), time: str = datetime.now().strftime("%H:%M:%S"), token: str = TOKEN1):
    
    graphql_query = f"""
    {{
        plan(
            from: {{lat: {start_coord[0]}, lon: {start_coord[1]}}},
            to: {{lat: {end_coord[0]}, lon: {end_coord[1]}}},
            date: "{day}",
            time: "{time}",
            numItineraries: 5,
            transportModes: [{{mode: BUS}}, {{mode: RAIL}}, {{mode:TRAM}}, {{mode:WALK}}]
            walkReluctance: 1.0,
            walkBoardCost: 120,
            minTransferTime: 60,
            walkSpeed: 2.0,
        ) {{
            itineraries {{
                duration
                legs {{
                    mode
                    startTime
                    endTime
                    from {{
                        name
                    }}
                    to {{
                        name
                    }}
                    trip {{
                        routeShortName
                    }}
                }}
            }}
        }}
    }}
    """
    response = requests.post(
        url=BASE_URL,
        headers={"Content-Type": "application/json", "digitransit-subscription-key": token},
        data=json.dumps({"query": graphql_query})
    )
    response.raise_for_status()
    return response.json()



def parse_arrival_prediction(api_response):
    stop_name = api_response['data']['stop']['name']
    stoptimes = api_response['data']['stop']['stoptimesWithoutPatterns']
    
    parsed_data = {}
    
    for stoptime in stoptimes:
        short_name = stoptime['trip']['route']['shortName']
        in_seconds = stoptime['realtimeArrival']
        destination = stoptime['headsign']
        realtime_arrival = f"{in_seconds//3600}:{(in_seconds%3600)//60}"
        parsed_data[short_name] = (realtime_arrival, stop_name, destination)
    
    return parsed_data


def parse_itineraries(data):
    itineraries = data['data']['plan']['itineraries']
    instructions = []
    durations = []

    for itinerary in itineraries:
        route_info = []
        durations.append(int((itinerary['legs'][-1]['endTime'] - itinerary['legs'][0]['startTime'])/60000))
        for leg in itinerary['legs']:
            mode = leg['mode']
            if mode == 'WALK':
                continue
            start_time = datetime.fromtimestamp(leg['startTime'] / 1000).strftime('%H:%M:%S')
            from_name = leg['from']['name']
            to_name = leg['to']['name']
            route_name = leg['trip']['routeShortName'] if leg['trip'] else 'N/A'

            #instruction = f"Mode: {mode}, Start: {start_time}, From: {from_name}, To: {to_name}, Route: {route_name}"
            instruction = f"{start_time} {route_name} {from_name} -> {to_name} "
            route_info.append(instruction)
        
        instructions.append(route_info)
    
    return instructions, durations


def main():

    # Show timetables specific stops
    for stop in STOPS:
        raw = arrival_predictions(stop)
        dictionary = parse_arrival_prediction(raw)
        for short_name, details in dictionary.items():
            print(f"{short_name}: {details[1]} -> {details[2]} {details[0]}")
        print()
    
    # itinerary instructions
    raw_data = find_routes(HOME, UNI)
    time.sleep(2)  # should make stuff asynchronous so this would not be needed
    instructions, durations = parse_itineraries(raw_data)
    for i, route in enumerate(instructions, 1):
        print(f"Route {i}: {durations[i-1]} min")
        for instruction in route:
            print(instruction)
        print()

main()


