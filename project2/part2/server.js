const express = require("express");
const multer = require("multer");
const path = require("path");
const AWS = require("aws-sdk");

const app = express();
const port = 80;

const sqs = new AWS.SQS({ region: "us-east-1" });
const ec2 = new AWS.EC2({ region: "us-east-1" });

const requestQueueUrl =
  "https://sqs.us-east-1.amazonaws.com/253833429053/1230704334-req-queue";
const responseQueueUrl =
  "https://sqs.us-east-1.amazonaws.com/253833429053/1230704334-resp-queue";

const appTierAmiId = "ami-07b42ea7faee36b9b";
const instanceType = "t2.micro";
const maxInstances = 20;
let flip = false;
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });
// Store results in this object
const results = {};

// POST endpoint for handling file uploads
app.post("/", upload.single("inputFile"), async (req, res) => {
  if (!req.file) {
    return res.status(400).send("No file uploaded.");
  }

  const fileName = path.parse(req.file.originalname).name;

  // Send message to request queue
  const params = {
    MessageBody: JSON.stringify({
      fileName: fileName,
      imageData: req.file.buffer.toString("base64"),
    }),
    QueueUrl: requestQueueUrl,
  };

  try {
    await sqs.sendMessage(params).promise();
    console.log(`Sent ${fileName} to Request Queue`);

    // Wait for result from the results object
    const result = await waitForResult(fileName);

    delete results[fileName];
    if (result) {
      res.send(`${fileName}:${result}`);
    } else {
      res.status(500).send("Error retrieving result.");
    }
  } catch (err) {
    console.error("Error communicating with App Tier:", err);
    res.status(500).send("Server error");
  }
});

// Helper function to wait for the result
async function waitForResult(fileName) {
  while (!results[fileName]) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return results[fileName];
}

// Poll for results and keep results populated
async function pollForResults() {
  const params = {
    QueueUrl: responseQueueUrl,
    MaxNumberOfMessages: 10,
    WaitTimeSeconds: 5,
  };

  try {
    const data = await sqs.receiveMessage(params).promise();
    if (data.Messages && data.Messages.length > 0) {
      console.log(`Received ${data.Messages.length} message(s)`);

      // Process each message
      await Promise.all(
        data.Messages.map(async (message) => {
          const body = JSON.parse(message.Body);
          console.log(`Checking message for file: ${body.fileName}`);

          // If the message contains the result for the file, store it in the results object
          results[body.fileName] = body.prediction;
          console.log(`Result stored for file: ${body.fileName}`);

          // Delete the message from the queue
          const deleteParams = {
            QueueUrl: responseQueueUrl,
            ReceiptHandle: message.ReceiptHandle,
          };
          await sqs.deleteMessage(deleteParams).promise();
          console.log(`Deleted message for file: ${body.fileName}`);
        })
      );
    } else {
      console.log("No messages in the queue.");
    }
  } catch (err) {
    console.error("Error polling for results:", err);
  }

  // Continue polling in the background
  setTimeout(pollForResults, 2000);
}

// Start polling for results
pollForResults();
async function autoScaleAppTier() {
    const sqsParams = {
      QueueUrl: requestQueueUrl,
      AttributeNames: ["ApproximateNumberOfMessages"],
    };
  
    try {
      const data = await sqs.getQueueAttributes(sqsParams).promise();
      const pendingMessages = parseInt(
        data.Attributes.ApproximateNumberOfMessages,
        10
      );
      const currentInstanceCount = await getAppInstanceCount();
  
      // Launch instances based on pending messages
      if (pendingMessages > 0 && currentInstanceCount < maxInstances) {
        const instancesToLaunch = Math.min(
          pendingMessages, 
          maxInstances - currentInstanceCount
        );
        console.log(
          `Pending messages: ${pendingMessages}. Launching ${instancesToLaunch} App Tier instance(s).`
        );
        await launchAppInstance();
      }
  
      // Stop instances if no pending messages and there are running instances
      if (pendingMessages === 0 && currentInstanceCount > 0) {
        console.log(
          "No pending messages. Waiting before stopping App Tier instances..."
        );
        await new Promise((resolve) => setTimeout(resolve, 30000));  // Wait 30 seconds before stopping
        await stopAppInstances();  // Use stop instead of terminate
      }
    } catch (err) {
      console.error("Error during autoscaling:", err);
    }
  }
  

 
async function getAppInstanceCount() {
  try {
    const params = {
      Filters: [
        { Name: "tag:Name", Values: ["app-tier-instance"] },
        { Name: "instance-state-name", Values: ["running","pending"] },
      ],
    };

    const instances = await ec2.describeInstances(params).promise();
    const runningInstances = instances.Reservations.flatMap(
      (reservation) => reservation.Instances
    );

    return runningInstances.length;  
  } catch (err) {
    console.error("Error retrieving instance count:", err);
    return 0;
  }
}

async function launchAppInstance() {
    try {
      // Check for stopped instances to start
      const params = {
        Filters: [
          { Name: "tag:Name", Values: ["app-tier-instance"] },
          { Name: "instance-state-name", Values: ["stopped"] },  // Find stopped instances to start
        ],
      };
  
      const instances = await ec2.describeInstances(params).promise();
      const stoppedInstanceIds = instances.Reservations.flatMap((reservation) =>
        reservation.Instances.map((instance) => instance.InstanceId)
      );
  
      if (stoppedInstanceIds.length > 0) {
        console.log(`Found stopped instances: ${stoppedInstanceIds}`);
        const batch = stoppedInstanceIds.slice(0, 3);
        await ec2.startInstances({ InstanceIds: batch }).promise();
        await new Promise(resolve => setTimeout(resolve, 2000));  // 2 seconds delay
        console.log(`Started all available stopped instances.`);
      } else {
        // If no stopped instances, launch new ones
        console.log(`No stopped instances available. Launching a new instance with AMI: ${appTierAmiId}`);
        const launchParams = {
          ImageId: appTierAmiId,
          InstanceType: instanceType,
          MinCount: 1,
          MaxCount: 1,
          TagSpecifications: [
            {
              ResourceType: "instance",
              Tags: [{ Key: "Name", Value: "app-tier-instance" }],
            },
          ],
        };
        const instance = await ec2.runInstances(launchParams).promise();
        console.log("Launched new App Tier instance:", instance.Instances[0].InstanceId);
      }
    } catch (err) {
      console.error("Error starting or launching App Tier instance:", err);
    }
  }
  

async function stopAppInstances() {
    try {
      const params = {
        Filters: [
          { Name: "tag:Name", Values: ["app-tier-instance"] },
          { Name: "instance-state-name", Values: ["running"] },  // Only stop running instances
        ],
      };
  
      const instances = await ec2.describeInstances(params).promise();
      const instanceIds = instances.Reservations.flatMap((reservation) =>
        reservation.Instances.map((instance) => instance.InstanceId)
      );
  
      if (instanceIds.length > 0) {
        console.log(`Stopping instances: ${instanceIds}`);
        await ec2.stopInstances({ InstanceIds: instanceIds }).promise();
        console.log("Stopped instances:", instanceIds);
      } else {
        console.log("No running instances to stop.");
      }
    } catch (err) {
      console.error("Error stopping App Tier instances:", err);
    }
  }
  
async function resetResults() {
    const count = await getAppInstanceCount()
    if(count === 0 && flip === true){
        results.length = 0
        console.log(`Results reset!!!!`)
    }
    else if(count === 0){
        flip = true;
    }
}

setInterval(resetResults,30000)
setInterval(autoScaleAppTier, 5000);

app.listen(port, () => {
  console.log(`Server running on http://localhost:${port}`);
});