import json 
import os
import boto3
import collections
import ast
def lambda_handler(event, context):
    print("Analyzing event")
    print(event)
    message = event['Records'][0]['Sns']['Message'] 
    jsonVal = json.loads(message);
    assessmentArn =jsonVal['run']  
    region=os.environ['AWS_DEFAULT_REGION']
    ec2 = boto3.client('ec2',region) 
    sns = boto3.client('sns',region) 
    inspector = boto3.client('inspector',region) 
    findingArns = inspector.list_findings(assessmentRunArns=[jsonVal['run']],maxResults=5000)
    aggregateData={}
    for findingArn in findingArns['findingArns']:
        finding = inspector.describe_findings(findingArns=[findingArn]) 
        for result in finding['findings']: 
            instanceId =result['assetAttributes']['agentId']
            severity =result['severity']
            cveName=result['id']
            if not (instanceId) in aggregateData:
                aggregateData[instanceId]={}
                aggregateData[instanceId]['findings']={}
                aggregateData[instanceId]['findings'][severity]=0
                instance=ec2.describe_instances(InstanceIds=[instanceId]);
                tagsStr=str(instance['Reservations'][0]['Instances'][0]['Tags']) 
                tagsStr =tagsStr.replace('Key','key').replace('Value','value')  
                aggregateData[instanceId]['tags']= ast.literal_eval(tagsStr)
            elif not (severity) in aggregateData[instanceId]['findings']:
                aggregateData[instanceId]['findings'][severity]=0
            aggregateData[instanceId]['findings'][severity]=aggregateData[instanceId]['findings'][severity]+1; 
            inspector.add_attributes_to_findings(findingArns=[result['arn']],attributes=aggregateData[instanceId]['tags'])
    tagsList=[]
    for key  in aggregateData: 
        outputJson=[] 
        for tag in aggregateData[key]['tags']:
            if tag['key'] != 'continuous-assessment-instance':
                outputJson.append("\""+tag['key']+"\""+":"+"\""+tag['value']+"\"")
        for sev in aggregateData[key]['findings']:
            outputJson.append("\"Finding-Severity-"+sev+"-Count\""+":"+"\""+str(aggregateData[key]['findings'][sev])+"\"")
        outputJson.sort()
        print(outputJson)
        tagsList.append('{'+', '.join(outputJson)+'}')
        print('Terminating:'+key)
        #ec2.terminate_instances(InstanceIds=[key],DryRun=False)
    sns.publish(TopicArn='arn:aws:sns:ap-southeast-2:027378719919:Builder-Notification-ContinuousAssessmentResultsTopic-ZXBWHQ22JGU0',Message='['+', '.join(tagsList)+']')
    return jsonVal['run']