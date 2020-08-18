
import json
import urllib.parse
import boto3
import time
import os
def lambda_handler(event, context):
    AMIsParamName = event['AMIsParamName'];
    region=os.environ['AWS_DEFAULT_REGION']
    ec2 = boto3.client('ec2',region)
    ssm = boto3.client('ssm',region)
    inspector = boto3.client('inspector',region)
    AmiJson =  ssm.get_parameter(Name=AMIsParamName)['Parameter']['Value']
    items = json.loads(AmiJson)
    for entry in items:
        images= ec2.describe_images(ImageIds=[entry['ami-id']],DryRun=False)
        tags = images['Images'][0]['Tags']
        tags.append({'Key': 'continuous-assessment-instance', 'Value': 'true'})
        ec2.run_instances(ImageId=entry['ami-id'],InstanceType=entry['instanceType'],UserData=entry['userData'],DryRun=False,MaxCount=1,MinCount=1,TagSpecifications=[{'ResourceType': 'instance','Tags': tags}])
    assessmentTemplateArn='';
    rules = inspector.list_rules_packages();
    
    millis = int(round(time.time() * 1000))
    existingTemplates = inspector.list_assessment_templates(filter={'namePattern': 'ContinuousAssessment'})
    print('Total templates found:'+str(len(existingTemplates['assessmentTemplateArns'])))
    if len(existingTemplates['assessmentTemplateArns'])==0:
        resGroup = inspector.create_resource_group(resourceGroupTags=[{'key': 'continuous-assessment-instance','value': 'true'}])
        target = inspector.create_assessment_target(assessmentTargetName='ContinuousAssessment',resourceGroupArn=resGroup['resourceGroupArn'])
        template = inspector.create_assessment_template(assessmentTargetArn=target['assessmentTargetArn'],assessmentTemplateName='ContinuousAssessment', durationInSeconds=3600,rulesPackageArns=rules['rulesPackageArns'])
        assessmentTemplateArn=template['assessmentTemplateArn']
        response = inspector.subscribe_to_event(event='ASSESSMENT_RUN_COMPLETED',resourceArn=template['assessmentTemplateArn'],topicArn='",{"Ref":"ContinuousAssessmentCompleteTopic"},"') ",
        print('Template Created:'+template['assessmentTemplateArn'])
    else:
         assessmentTemplateArn=existingTemplates.get('assessmentTemplateArns')[0]
    time.sleep(240)
    run = inspector.start_assessment_run(assessmentTemplateArn=assessmentTemplateArn,assessmentRunName='ContinuousAssessment'+'-'+str(millis))
    return 'Done'