"""Adds mangum support for lambda deployment."""

from mangum import Mangum

from main import app

handler = Mangum(app, lifespan="off", api_gateway_base_path="/default-deployment")
