# Project 2: AWS-Based Face Recognition Pipeline

This project implements a serverless, event-driven architecture on AWS to perform face recognition on user-uploaded videos.
Utilizing AWS Lambda, S3, and Docker, the application processes videos by extracting frames and identifying faces using a pre-trained CNN model.

## Features

- **Video Upload**: Users upload videos to an S3 input bucket.
- **Frame Extraction**: An AWS Lambda function, triggered by the upload event, splits videos into individual frames using FFmpeg.
- **Face Recognition**: Another Lambda function, packaged with a Docker container, processes frames to detect faces using a pre-trained CNN model.
- **Results Storage**: Recognition results are stored as text files in an S3 output bucket.

## Setup Instructions

1. **AWS Configuration**:
   - Ensure AWS CLI is installed and configured with appropriate credentials.
   - Set up the necessary IAM roles with permissions for S3 and Lambda.

2. **S3 Buckets**:
   - Create three S3 buckets:
     - `input-bucket` for video uploads.
     - `frame-bucket` for storing extracted frames.
     - `output-bucket` for storing recognition results.

3. **Lambda Functions**:
   - **Frame Extraction Function**:
     - Use FFmpeg to extract frames from videos.
     - Trigger: S3 `input-bucket` upload event.
   - **Face Recognition Function**:
     - Packaged with a Docker container containing the pre-trained CNN model.
     - Trigger: S3 `frame-bucket` upload event.

4. **Testing**:
   - Upload a sample video to the `input-bucket`.
   - Monitor the `output-bucket` for the results file containing recognized faces.

Ensure all AWS resources are correctly configured and that the Lambda functions have the necessary permissions to access S3 buckets.
