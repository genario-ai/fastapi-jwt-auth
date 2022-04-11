#!/usr/bin/env bash

pipenv run pytest --cov=tests --cov-report=term-missing --cov-report=html -v
