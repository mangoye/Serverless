import sys
import json
import boto3
from chalice import Chalice, Response, BadRequestError, NotFoundError
from chalice import CORSConfig
from botocore.exceptions import ClientError
from chalice import CognitoUserPoolAuthorizer

if sys.version_info[0] == 3:
    # Python 3 imports.
    from urllib.parse import urlparse, parse_qs
else:
    # Python 2 imports.
    from urlparse import urlparse, parse_qs
#
#
#

app = Chalice(app_name='helloworld')
app.debug = True

# Must be integrated with Terraform
# /!\ Terraform must write the execution IAM policy in advance with S3:GetObject and S3:PutObject
S3 = boto3.client('s3', region_name='us-east-1')
BUCKET = 'mangoyes-chalice'


CITIES_TO_STATE = {
    'seattle': 'WA',
    'portland': 'OR',
}

OBJECTS = {
}

cors_config = CORSConfig(
    allow_origin='http://example.com',
    allow_headers=['X-Special-Header'],
    max_age=600,
    expose_headers=['X-Special-Header'],
    allow_credentials=True
    )


@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/cities/{city}')
def state_of_city(city):
    try:
        return {'state': CITIES_TO_STATE[city]}
    except KeyError:
        raise BadRequestError("Unknown city '%s', valid choices are: %s" % (
            city,','.join(CITIES_TO_STATE.keys())))

@app.route('/resource/{value}', methods=['PUT'])
def put_test(value):
    try:
        return {"value": value}
    except KeyError:
        raise ForbiddenError("Il y'a une erreur...")

@app.route('/myview', methods=['POST', 'PUT'])
def myview():
    pass

@app.route('myview2', methods=['POST'])
def myview2():
    pass

@app.route('myview2', methods=['PUT'])
def myview2():
    pass

# Policy generation --> Store the object we get in AWS S3 with boto 3 
# Must be tested later on with AWS DynamoDB and AWS Cognito >>>
# /!\ One route that can handles multiple methods.
#Can be tested with: echo '{"foo": "bar"}' | http PUT https://endpoint/api/objects/mykey
@app.route('/objects/{key}', methods=['GET', 'PUT'])
def s3objects(key):
    request = app.current_request
    if request.method == 'PUT':
        S3.put_object(Bucket=BUCKET, Key=key,
            Body=json.dumps(request.json_body))
    elif request.method == 'GET':
        try:
            response = S3.get_object(Bucket=BUCKET, Key=key)
            return json.loads(response['Body'].read())
        except ClientError as e:
            raise NotFoundError(key)

# can be tested like: http 'https://endpoint/api/introspect?query1=value1&query2=value2' 'X-TestHeader: Foo'
@app.route('/introspect')
def introspect():
    return app.current_request.to_dict()

# Chalice can manage specific content-type
# It must be tested like: http --form POST https://endpoint/api/formtest states=WA states=CA --debug
@app.route('/content-type', methods=['POST'], content_types=['application/x-www-form-urlencoded'])
def contenttype():
    parsed = parse_qs(app.current_request.raw_body.decode())
    return {
        'states' : parsed.get('states',[])
    }

# Customize HTTP response
@app.route('/index')
def indexcustom():
    return Response(body='hello world! this is a custom response 200 from chalice',
        status_code=200,
        headers={'Content-Type':'text/plain'})

# Support CORS - Corss-Origin Resource Sharing = allow restricted resources such as fonts/images to be requested from another domain
# Settings cors=True has similar behavior to enabling CORS using the AWS Console.
@app.route('/support-cors', methods=['PUT'], cors=True)
def support_cors():
    return {}

@app.route('/custom_cors', methods=['GET'], cors=cors_config)
def support_custom_cors():
    return {'cors': True}

# Authentication : API Key
# Only requests sent with a valid X-Api-Key header will be accepted.
@app.route('/authenticated', methods=['GET'], api_key_required=True)
def authenticated():
    return {"secure": True}

# Authentication : Using Amazon Cognito User Pools
# /!\ Must be configured --> First create an user and get his token. Then send the token in the request...
authorizer = CognitoUserPoolAuthorizer(
    'MyUserPoolChalice', header='Authorization',
    provider_arns=['arn:aws:cognito-idp:us-east-1:789657502505:userpool/name'])

@app.route('/users-pools', methods=['GET'], authorizer=authorizer)
def authenticatedCongnito():
    return {"secure": True}
    