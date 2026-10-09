from sqlalchemy import Column, Integer, BigInteger, Text, JSON, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .db import Base

class Channel(Base):
    __tablename__ = "channel"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(Text, nullable=False)           # e.g., "NASA SMAP", "NASA MSL", "DEMO"
    channel_key = Column(Text, nullable=False)      # e.g., "P-1", "S-1", "PWR.BATT_TEMP"
    units = Column(Text, default="Normalized (-1 to 1)")
    subsystem = Column(Text, default="Unknown / Unspecified")
    anomaly_type = Column(Text, default="Unspecified") # e.g. "point", "contextual"
    meta_info = Column(JSON, nullable=True)

    __table_args__ = (UniqueConstraint("source", "channel_key", name="uq_source_channel"),)

class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False, index=True)
    timestep = Column(Integer, nullable=True, index=True) # Integer timestep for Telemanom
    ts = Column(Text, nullable=True, index=True)           # ISO timestamp string
    value = Column(Float, nullable=False)
    quality = Column(Text, default="nominal")

class Anomaly(Base):
    __tablename__ = "anomaly_detection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False, index=True)
    window_start = Column(Text, nullable=True)
    window_end = Column(Text, nullable=True)
    start_step = Column(Integer, nullable=True)
    end_step = Column(Integer, nullable=True)
    score = Column(Float, nullable=False)
    label = Column(Boolean, default=True)
    method = Column(Text, nullable=False)                  # "zscore", "isoforest", etc.
    severity = Column(Text, default="warning")             # "warning", "critical"
    evidence = Column(JSON, nullable=True)                 # Statistical evidence dictionary

class Benchmark(Base):
    __tablename__ = "benchmark_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel = Column(Text, nullable=False)
    method = Column(Text, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1 = Column(Float, nullable=False)
