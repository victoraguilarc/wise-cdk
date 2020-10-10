# Wise CDK

Infraestructure as code to build and deploy `django-wise` projects to AWS using:  
- RDS (Postgres)
- Elasticache (Redis)
- ECS Fargate
- S3 Bucket for statics

> This project is focused in deployment only. all testing/linting and pre deploy tasks should be managed in another engines, 
> I recommend you Github Actions.

## Installation

#### 1. Create  manually the following resources in AWS.

 1. A S3 bucket for the pipeline artifacts, necesary to keep the AWS pipeline artifacs
 2. A SSL certificate for requiered domains, you'll need move NS domain records to Route53
 3. Create user with enough permissions to run CDK tasks, and get his `aws_client_id` and `aws_client_secret`
    The user should be able to execute RDS, Elasticache, S3, VPC, ECS tasks
 4. Create an s3 bucket for pipeline artifacts and use its name in `cdk.stacks.json` file in the `artifact_bucket` key.
 5. Create the following configuration files and place them in the root of the project.

    **`.env`**
    ```
    AWS_DEFAULT_REGION=...
    AWS_REGION=...
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_ACCOUNT_ID=...
    ``` 
    **`cdk.stacks.json`**
    ```
    [
        {
            "stack_name": "<stack-name>",
            "kms_key_uuid": "KMS item UUID",
            "cache_node_type": "AWS Redis node types",
            "num_cache_nodes": 1,
            "database_size": "AWS RDS size",
            "database_name": "anything",
            "database_username": "something",
            "database_allocated_storage": 25,
            "database_encrypted": false,
            "artifact_bucket": "s3 Bucket name for artifacts",
            "certificate_key_id": "Certificate manager Item UUID",
            "repo_owner": "name or organization",
            "repo_name": "repository",
            "repo_branch": "something",
            "dns_name": "main domain",
            "dns_zone_id": "main domain id in route53",
            "dns_stack_subdomain": "stack subdomain just the left side",
            "github_access_token": "Personal access token generate in GitHub",
            "enable_deploy_approval": false
        },
        {...}
    ]
    ```
    
 
#### 2. Install Docker, Docker compose and make 

This step is different acording your SO.
One you have all of this, exec the build command.

#### 3. Build Project containers
```
make build
```

#### 4. Usage
1. Deploy VPC first

    ```
    $ make deploy STACK=<stack-name>-vpc
    ```
2. Deploy Main Stack
    ```
    $ make deploy STACK=<stack-name>
    ```
3. Check camges
    ```
    $ make diff STACK=<stack-name>
    ```

## Environment Variables Management

`django-wise` template manages environment variables dynamically using `chamber` for this.
To configure `chamber ` you need to do the following:

1. Create a KMS Key (Region could be different)
    https://console.aws.amazon.com/kms/home?region=us-east-1#/kms/keys/create
2. Setup its alias as `parameter_store_key`
3. Copy its `Key ID` and use it in the **`cdk.stacks.json`** config file for `kms_key_uuid` key.


### Pending Guides

1, How to setup domain in `Route53`?
2. How to setup SSL Certificates in `Certificate Manager`?
5. How to get github access token?
