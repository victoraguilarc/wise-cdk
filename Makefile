.PHONY: docs coverage fixtures
.SILENT: clean

SERVICE=platform-api-staging

clean:
	@echo "Cleaning containers ..."
	docker ps -aq | xargs docker stop
	docker ps -aq | xargs docker rm

build:
	docker-compose build
	@echo "Building..."

synth:
	docker-compose run --rm infra cdk synth $(SERVICE)

diff:
	docker-compose run --rm infra cdk diff $(SERVICE)

deploy:
	docker-compose run --rm infra cdk deploy $(SERVICE)

destroy:
	docker-compose run --rm infra cdk destroy $(SERVICE)


# chamber list platform-api-staging
upload_environment:
	docker-compose run --rm infra /chamber import $(SERVICE) .envs/$(SERVICE).json

download_environment:
	docker-compose run --rm infra /chamber export --format json  $(SERVICE) | jq . > env.$(SERVICE).json

shell:
	docker-compose run --rm infra bash



