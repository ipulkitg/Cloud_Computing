import boto3
import base64
import json
import torch
from PIL import Image
from io import BytesIO
from facenet_pytorch import MTCNN, InceptionResnetV1

sqs = boto3.client('sqs', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

request_queue_url = 'https://sqs.us-east-1.amazonaws.com/253833429053/1230704334-req-queue'
response_queue_url = 'https://sqs.us-east-1.amazonaws.com/253833429053/1230704334-resp-queue'

input_bucket_name = '1230704334-in-bucket'
output_bucket_name = '1230704334-out-bucket'

mtcnn = MTCNN(image_size=240, margin=0, min_face_size=20)
resnet = InceptionResnetV1(pretrained='vggface2').eval()

saved_data = torch.load('data.pt')
embedding_list = saved_data[0]
name_list = saved_data[1]

def face_match(image: Image):
    face, prob = mtcnn(image, return_prob=True)
    if face is None:
        return "No face detected"

    emb = resnet(face.unsqueeze(0)).detach()

    dist_list = []
    for idx, emb_db in enumerate(embedding_list):
        dist = torch.dist(emb, emb_db).item()
        dist_list.append(dist)

    idx_min = dist_list.index(min(dist_list))
    return name_list[idx_min], min(dist_list)

def upload_image_to_s3(file_name, image_data):
    try:
        s3.put_object(Bucket=input_bucket_name, Key=file_name, Body=image_data)
        print(f"Image {file_name} uploaded to S3 bucket {input_bucket_name}")
    except Exception as e:
        print(f"Error uploading image to S3: {str(e)}")

def upload_result_to_s3(file_name, result):
    try:
        s3.put_object(Bucket=output_bucket_name, Key=file_name, Body=result)
        print(f"Result {result} uploaded to S3 bucket {output_bucket_name}")
    except Exception as e:
        print(f"Error uploading result to S3: {str(e)}")

def process_message():
    response = sqs.receive_message(
        QueueUrl=request_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )

    if 'Messages' not in response:
        return

    for message in response['Messages']:
        message_body = message['Body']
        message_data = json.loads(message_body)

        file_name = message_data['fileName']
        image_data = base64.b64decode(message_data['imageData'])

        upload_image_to_s3(f"{file_name}.jpg", image_data)

        image = Image.open(BytesIO(image_data))

        try:
            name, distance = face_match(image)
            print(f"Recognized {name} with distance {distance}")

            upload_result_to_s3(file_name, name)
            result_message = {
                'fileName': file_name,
                'prediction': name
            }
            sqs.send_message(
                QueueUrl=response_queue_url,
                MessageBody=json.dumps(result_message)
            )

            sqs.delete_message(
                QueueUrl=request_queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )

        except Exception as e:
            print(f"Error processing image {file_name}: {str(e)}")

if __name__ == '__main__':
    while True:
        process_message()
