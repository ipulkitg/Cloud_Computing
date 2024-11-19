import json
import logging
import boto3
import os
import subprocess
import math


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def video_splitting_cmdline(video_filename):
    video_name = os.path.basename(video_filename)
    outfile = os.path.splitext(video_name)[0] + ".jpg"

    frame_extraction_command = 'ffmpeg -i ' + video_filename + ' -vframes 1 ' + '/tmp/' + outfile
    try:
        subprocess.check_call(frame_extraction_command, shell=True)
    except subprocess.CalledProcessError as e:
        print(e.returncode)
        print(e.output)

    fps_extraction_command = 'ffmpeg -i ' + video_filename + ' 2>&1 | sed -n "s/.*, \\(.*\\) fp.*/\\1/p"'
    fps = subprocess.check_output(fps_extraction_command, shell=True).decode("utf-8").rstrip("\n")
    return outfile


def uploadframes(out_file, output_bucket):
    s3_client = boto3.client('s3')
    image_path = '/tmp/' + out_file
    with open(image_path, 'rb') as file:
        s3_client.upload_fileobj(file, output_bucket, out_file)

    lambda_client = boto3.client('lambda')

    lambda_payload = {
        'bucket_name': output_bucket,
        'image_file_name': out_file
    }
    
    response = lambda_client.invoke(
        FunctionName = "face-recognition",
        InvocationType = 'Event',
        Payload = json.dumps(lambda_payload)
    )

def lambda_handler(event, context):
    try:
        # defining input and output bucket
        input_bucket_name = '1230704334-input'
        output_bucket = "1230704334-stage-1"

        vid_filename = event['Records'][0]['s3']['object']['key']
        s3_client = boto3.client('s3')
        download_path = '/tmp/' + vid_filename
        s3_client.download_file(input_bucket_name, vid_filename, download_path) # downloading the video file and saving it to the tmp folder
        out_file = video_splitting_cmdline(download_path) # receiving the output dir from the funciton
        
        # uploading the output dir to s3 output bucket
        uploadframes(out_file=out_file, output_bucket=output_bucket)
        
        return {
        'statusCode': 200,
        'body': json.dumps('Video Splitting Successful...')
    }
    
    except Exception as e:
        logger.error("An error occured...%s", str(e))
        raise e
        
    
    