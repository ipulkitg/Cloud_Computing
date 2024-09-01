import boto3
import time
import os

# Initialize AWS clients
ec2 = boto3.resource('ec2')
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Function to create an EC2 instance
def create_ec2_instance(key_pair_name):
    instance = ec2.create_instances(
        # Example Ubuntu AMI ID for us-east-1
        ImageId='ami-0b69ea66ff7391e80',
        InstanceType='t2.micro',
        KeyName=key_pair_name,
        MinCount=1,
        MaxCount=1,
        TagSpecifications=[{'ResourceType': 'instance',
                            'Tags': [
                            {
                            'Key': 'Name',
                            'Value': 'App Tier Worker'
                            }
                            ]}]
    )
    instance_id = instance[0].id
    print(f'EC2 Instance creation successful! The new instance has been assigned an ID of {instance_id}.')
    return instance_id

# Function to create an S3 bucket
def create_bucket(bucket_name):
    response = s3.create_bucket(
        Bucket=bucket_name
    )
    print(f'Your new S3 Bucket, {bucket_name}, has been successfully created.')
    return bucket_name

# Function to create SQS queue
def create_queue(queue_name):
    response = sqs.create_queue(
        QueueName=queue_name,
        Attributes={'FifoQueue': 'true', 'ContentBasedDeduplication': 'true'}
    )
    print(f'SQS FIFO Queue creation complete: {queue_name} is now available for use.')
    return response['QueueUrl']

# List EC2 instances
def list_ec2_instance():
    print("Listing EC2 instances:")
    instances = ec2.instances.all()
    for instance in instances:
        print(f'Instance ID: {instance.id}, State: {instance.state["Name"]}')

# List S3 buckets
def list_buckets():
    print("Listing S3 buckets:")
    buckets = s3.list_buckets()
    for bucket in buckets['Buckets']:
        print(f'Bucket Name: {bucket["Name"]}')

# List SQS queues
def list_queues():
    print("Listing SQS queues:")
    response = sqs.list_queues()
    for queue_url in response.get('QueueUrls', []):
        print(f'Queue URL: {queue_url}')

# Upload file to S3
def upload_file(bucket_name, file_name):
    with open(file_name, "w") as f:
        f.write("")
    s3.upload_file(file_name, bucket_name, file_name)
    os.remove(file_name)
    print(f"Uploaded {file_name} to S3 bucket {bucket_name}")

# Send message to SQS queue
def send_message_to_queue(queue_url, message_name, message_body, message_group_id):
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body,
        MessageAttributes={
            'Title': {
                'StringValue': message_name,
                'DataType': 'String'
            }
        },
        MessageGroupId = message_group_id
    )
    print("Message sent")

# Get number of messages in SQS queue
def get_queue_count(queue_url):
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    message_count = response['Attributes']['ApproximateNumberOfMessages']
    print(f"Number of messages in queue: {message_count}")
    return message_count

# Receive message from SQS queue
def receive_message_from_sqs(queue_url):
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MessageAttributeNames=['All'],
        MaxNumberOfMessages=1
    )
    messages = response.get('Messages', [])
    if messages:
        message = messages[0]
        receipt_handle = message['ReceiptHandle']
        message_body = message['Body']
        message_name = message['MessageAttributes']['Title']['StringValue']
        print(f"Received message: {message_name}")
        print(f"Message body: {message_body}")
        # Delete the message after reading it
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        print("Message deleted after processing")
    else:
        print("No messages found")

# Delete all resources
def delete_resources(instance_id, bucket_name, queue_url):
    # Terminate EC2 instance
    ec2.Instance(instance_id).terminate()
    print(f"Terminated EC2 instance {instance_id}")
    
    response = s3.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        for obj in response['Contents']:
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            print(f"Deleted {obj['Key']} from S3 bucket {bucket_name}")
    # Delete S3 bucket
    s3.delete_bucket(Bucket=bucket_name)
    print(f"Deleted S3 bucket {bucket_name}")
    
    # Delete SQS queue
    sqs.delete_queue(QueueUrl=queue_url)
    print(f"Deleted SQS queue {queue_url}")

if __name__ == '__main__':
    # Define resource names
    key_pair_name = 'key_pair1' # Your key pair
    s3_bucket_name = 'project00001'  # Must be unique
    sqs_queue_name = 'CSE546test.fifo'  # Must end with .fifo

    # Create EC2 instance, S3 bucket, and SQS queue
    instance_id = create_ec2_instance(key_pair_name)
    s3_bucket_name = create_bucket(s3_bucket_name)
    sqs_queue_url = create_queue(sqs_queue_name)
    
    print("Request sent, wait for 1 min")
    time.sleep(60)
    
    # List EC2 instances, S3 buckets, and SQS queues
    list_ec2_instance()
    list_buckets()
    list_queues()
    
    # Upload a file to the S3 bucket
    upload_file(s3_bucket_name, "CSE546test.txt")
    
    # Send a message to the SQS queue
    send_message_to_queue(sqs_queue_url, "test message", "This is a test message", "testGroup")
    
    # Check number of messages in SQS queue
    get_queue_count(sqs_queue_url)
    
    print("Waiting for resource preview")
    time.sleep(60)
    
    # Receive message from SQS queue
    receive_message_from_sqs(sqs_queue_url)
    
    # Check number of messages in SQS queue again
    get_queue_count(sqs_queue_url)
    
    print("Waiting for 30 seconds before deleting resources")
    time.sleep(30)
    
    # Delete all resources
    delete_resources(instance_id, s3_bucket_name, sqs_queue_url)
    
    print("Waiting for 20 seconds to confirm deletion")
    time.sleep(20)
    
    # List resources again to confirm deletion
    list_ec2_instance()
    list_buckets()
    list_queues()