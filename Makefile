.PHONY: docs coverage fixtures
.SILENT: clean

STACK=platform-api-staging

clean:
	@echo "Cleaning containers ..."
	docker ps -aq | xargs docker stop
	docker ps -aq | xargs docker rm

build:
	docker-compose build
	@echo "Building..."

synth:
	docker-compose run --rm infra cdk synth $(STACK)

diff:
	docker-compose run --rm infra cdk diff $(STACK)

deploy:
	docker-compose run --rm infra cdk deploy $(STACK)

destroy:
	docker-compose run --rm infra cdk destroy $(STACK)


# chamber list platform-api-staging
upload_environment:
	docker-compose run --rm infra /chamber import $(STACK) .envs/$(STACK).json

download_environment:
	docker-compose run --rm infra /chamber export --format json  $(STACK) | jq . > env.$(STACK).json

shell:
	docker-compose run --rm infra bash



