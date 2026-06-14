"""Coracle Engine - Core processing modules."""
from engine.ingestor import SignalIngestor
from engine.processor import SignalProcessor
from engine.sacred_gate import SacredGate
from engine.confluence import ConfluenceEngine
from engine.contract_generator import ContractGenerator
from engine.compounding import CompoundingEngine

__all__ = [
    "SignalIngestor",
    "SignalProcessor", 
    "SacredGate",
    "ConfluenceEngine",
    "ContractGenerator",
    "CompoundingEngine"
]


