import googlemaps
import boto3
from langchain.prompts.prompt import PromptTemplate
import json
from dotenv import load_dotenv
import os

load_dotenv()
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_access_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
gmap_api_key = os.getenv("GOOGLE_MAP_API_KEY")

# establish bedrock clients
client = boto3.client('bedrock')
runtime = boto3.client('bedrock-runtime', 'us-east-1', 
                        endpoint_url="https://bedrock-runtime.us-east-1.amazonaws.com",
                        aws_access_key_id= aws_access_key,
                        aws_secret_access_key= aws_access_secret,
                        )
model_id = 'anthropic.claude-v2'
accept = "application/json"
contentType = "application/json"

# instantiate gmaps client
gmaps = googlemaps.Client(gmap_api_key) #replace with your key

def places_recommendations(location: dict, radius: float, place: str) -> list:
    locations = []
    places = gmaps.places_nearby(location=location, radius=radius, keyword=place)
    for place in places['results']:
        locations.append([{"Name": place['name'], "Address": place['vicinity'], "Rating": place['rating']}])
    return locations

def curate_recommendations(location: str, distance: int, cuisine: str, activity: str) -> tuple:
    coordinates = gmaps.geocode(location)
    loc_coordinates = coordinates[0]['geometry']['location']
    radius = distance * 1609.34 #convert miles to meters for maps API
    print('radius', radius)
    food_recs = places_recommendations(loc_coordinates, radius, cuisine)
    activity_recs = places_recommendations(loc_coordinates, radius, activity)
    print('food_recs', food_recs)
    print('activity_recs', activity_recs)
    return (food_recs, activity_recs)

def invoke_bedrock(input_prompt: str, model_id: str = 'anthropic.claude-v2', accept: str = 'application/json', 
                   contentType: str = 'application/json') -> str:
    body = json.dumps({"prompt": input_prompt, "max_tokens_to_sample": 500})
    response = runtime.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    output = response_body.get("completion")
    return output

# Prompt Template Setup
claude_template = """Human: Generate a date idea based off of the information that has been provided:
User/Requester Location: {location}
Cuisine/Restaurant: {cuisine}
Top locations for desired cuisine in location inputted: {food_recommendations}
Secondary interests/activites along with food for date: {activity}
Top locations for desired secondary activity in location inputted: {activity_recommendations}
Based off of the interests and recommendations provided and also using your existing knowledge of the location provided, give an end to end date idea.

Assistant:
"""

date_prompt = PromptTemplate(
    input_variables=["location", "cuisine", "food_recommendations", "activity", "activity_recommendations"],
    template=claude_template
)