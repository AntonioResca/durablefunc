import azure.functions as func
import azure.durable_functions as df
import logging
import matplotlib.pyplot as plt
import numpy as np
import os

import base64

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# An HTTP-triggered function with a Durable Functions client binding
@myApp.route(route="orchestrators/{functionName}")
@myApp.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client):

    nCluster = req.params.get('nCluster')
    if not nCluster:
        return func.HttpResponse(
            "Devi fornire 'nCluster' come parametro di query. Esempio: ?nCluster=5",
            status_code=400
        )

    function_name = req.route_params.get('functionName')
    instance_id = await client.start_new(function_name, None, nCluster)
    response = client.create_check_status_response(req, instance_id)
    return response


@myApp.function_name(name="GetResult")
@myApp.route(route="start/result")
@myApp.durable_client_input(client_name="client")
async def get_result(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    instance_id = req.params.get('instanceId')
    if not instance_id:
        return func.HttpResponse("Parametro 'instanceId' mancante.", status_code=400)

    status = await client.get_status(instance_id)

    if not status:
        return func.HttpResponse("Instance ID non trovato.", status_code=404)

    if status.runtime_status != "Completed":
        return func.HttpResponse(f"Stato attuale: {status.runtime_status}", status_code=202)

    # Prendi i dati binari
    grafico_base64 = status.output  # output è base64

    # Decodifica base64
    grafico_bytes = base64.b64decode(grafico_base64)

    # Torna immagine HTTP response
    return func.HttpResponse(
        body=grafico_bytes,
        mimetype="image/jpeg",
        status_code=200
    )

# Orchestrator
@myApp.orchestration_trigger(context_name="context")
def hello_orchestrator(context):
    nCluster = context.get_input()
    grafico_bytes = yield context.call_activity("CreaGraficoActivity", nCluster)
    return grafico_bytes


@myApp.function_name(name="CreaGraficoActivity")
@myApp.activity_trigger(input_name="nCluster")
def crea_grafico(nCluster: int) -> bytes:
    logging.info(f"Inizio creazione grafico con nCluster = {nCluster}")

    # Simula lunga elaborazione
    import time
    time.sleep(30)  

    # Percorso relativo al file pinguino.jpeg
    current_dir = os.path.dirname(__file__)
    img_path = os.path.join(current_dir, "pinguino.jpeg")

    if not os.path.exists(img_path):
        logging.error(f"Immagine non trovata: {img_path}")
        raise FileNotFoundError(f"Immagine non trovata: {img_path}")

    # Legge il file immagine come bytes
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    # Codifica in Base64
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')


    return img_base64