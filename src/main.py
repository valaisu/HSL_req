import requests
import json
from datetime import datetime
import time
from PIL import Image, ImageDraw, ImageFont

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


def routes_graphical_representation(data, bar_height: int = 30, bar_medium: int = 15, window_size: int = 300, padding: int = 25):

    # first parse date into formats:
    # instructions = list[list[start_time, end_time, route_name, tansport_mode]]
    # where an element outer list is a full route and an element inner list is a bus ride / walk / etc.
    # durations = list[start_time: str, duration: str]

    itineraries = data['data']['plan']['itineraries']
    instructions = []
    duration_data = []
    now = int(datetime.now().timestamp())
    last_arrival = 0
    for itinerary in itineraries:
        duration = (int((itinerary['legs'][-1]['endTime'] - itinerary['legs'][0]['startTime'])/60000))
        start = datetime.fromtimestamp(itinerary['legs'][0]['startTime'] / 1000).strftime('%H:%M')        
        duration_data.append(f"{start}, {duration} min")
        route_info = []
        for leg in itinerary['legs']:
            mode = leg['mode']
            start_time = int(leg['startTime'] / 1000)
            end_time = int(leg['endTime'] / 1000)
            if (end_time > last_arrival): last_arrival = end_time
            route_name = leg['trip']['routeShortName'] if leg['trip'] else ''
            vehicle = [start_time, end_time, route_name, mode]
            route_info.append(vehicle)
        
        instructions.append(route_info)
    
    # transfer to graphical instructions
    # list[x_up_corner: int, y_up_corner: int, x_low_corner: int, y_low_corner: int, trnasport_line: str, transport_mode: str]
    # the list is named boxes
    time_window = last_arrival - now  # in seconds
    element_counter = 0
    boxes = []
    color_dict = {'WALK': 'grey', 'BUS': 'blue', 'TRAM': 'green', 'TRAIN': 'violet'}
    for instr in instructions:
        for vehicle in instr:
            start_pos_x = padding + window_size*(vehicle[0]-now)/time_window
            end_pos_x = padding + window_size*(vehicle[1]-now)/time_window
            start_pos_y = padding + element_counter*(bar_height+bar_medium)
            end_pos_y = padding + element_counter*(bar_height+bar_medium) + bar_height
            if start_pos_x < end_pos_x and start_pos_y < end_pos_y:
                boxes.append([start_pos_x, start_pos_y, end_pos_x, end_pos_y, vehicle[2], color_dict[vehicle[3]]])
        element_counter += 1

    print(boxes)

    # draw 
    img = Image.new('RGB', (450, 300), color='white')
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 12)
    
    # borders
    d.rounded_rectangle([padding-10, padding-10, padding+10+window_size, window_size-padding], outline='blue', width=2, radius=3)

    # transport
    for b in boxes:
        d.rounded_rectangle([b[0], b[1], b[2], b[3]], outline=b[5], width=3, radius=3)
        x_center = int((b[0]+b[2])/2)
        y_center = int((b[1]+b[3])/2)
        d.text((x_center-len(b[4])*3, y_center-6), b[4], fill=b[5], font=font)

    # durations
    for i, text in enumerate(duration_data):
        x_pos = window_size+padding+30
        y_pos = padding + 6 + i*(bar_height+bar_medium)
        print(x_pos, y_pos)
        d.text((x_pos, y_pos), text, fill='black', font=font)

    img.show()




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
    
    routes_graphical_representation(raw_data)


main()


