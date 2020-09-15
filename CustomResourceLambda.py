import boto3
import warnings
from botocore.vendored import requests
import json


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False):
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    responseUrl = event['ResponseURL']
    print(responseUrl)

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData

    json_responseBody = json.dumps(responseBody)

    print('Response body:\n' + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl, data=json_responseBody, headers=headers)
        print('Status code: ' + response.reason)
    except Exception as e:
        print('send(..) failed executing requests.put(..): ' + str(e))


def lambda_handler1(event, context):
    print(event)
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    send(event, context, SUCCESS, event)


def lambda_handler(event, context):
    print(event)
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    try:
        subnets = event['ResourceProperties']['Subnets']
        security_groups = event['ResourceProperties']['SecurityGroups']
        cluster_id = event['ResourceProperties']['ClusterId']
        task_df = event['ResourceProperties']['TaskDefinition'].split("/")[-1]

        if event['RequestType'] == 'Create':
            client = boto3.client('ecs')
            response = client.run_task(
                cluster=cluster_id,  # name of the cluster
                launchType='FARGATE',
                taskDefinition=task_df,  # replace with your task definition name and revision
                count=1,
                platformVersion='LATEST',
                networkConfiguration={
                    'awsvpcConfiguration': {
                        # 'subnets': [
                        #     'subnet-10a0152e',  # replace with your public subnet or a private with NAT
                        #     'subnet-1b5b6a51'  # Second is optional, but good idea to have two
                        # ],
                        'subnets': subnets,
                        'securityGroups': security_groups,
                        'assignPublicIp': 'ENABLED'
                    }
                })
            print(response)
            task_arn = response["tasks"][0]["taskArn"]
            send(event, context, SUCCESS, event, task_arn)
        elif event['RequestType'] == 'Delete':
            task_arn = event['PhysicalResourceId']
            if task_arn is None:
                err = "Couldn't find the TaskARN in Physical ID"
                print(err)
                send(event, context, FAILED, {"Error": err})

            print(f"TaskARN:{task_arn}")
            client = boto3.client('ecs')
            response = client.stop_task(
                cluster=cluster_id,
                task=task_arn
            )
            print(response)
            send(event, context, SUCCESS, {"Response": str(response)})
        elif event['RequestType'] == 'Update':
            # TODO Implement for Update
            send(event, context, FAILED, {"Error": "Logic Not implemented Yet"})

    except Exception as err:
        print(err)
        return send(event, context, FAILED, {"Error": str(err)})
