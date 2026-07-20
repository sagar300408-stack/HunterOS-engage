from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import logging

logger = logging.getLogger("hunteros.tracing")

def configure_tracing(app, engine):
    """
    Configures OpenTelemetry distributed tracing for FastAPI and SQLAlchemy.
    """
    provider = TracerProvider()
    
    # For now, export to console. In prod, this would be OTLPExporter to Jaeger/Tempo.
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument SQLAlchemy
    if engine:
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine if hasattr(engine, 'sync_engine') else engine
        )
        
    logger.info("Distributed tracing configured.")

def get_tracer(name: str):
    return trace.get_tracer(name)
