
from pydantic import BaseModel, Field
from typing import Optional, List
import yaml, pathlib

class VISAConfig(BaseModel):
    resource: Optional[str] = Field(None, description="VISA resource string, e.g. TCPIP0::192.168.1.50::INSTR")
    timeout_ms: int = Field(5000)

class VNAConfig(BaseModel):
    vendor: str = Field("siglent", description="siglent or rigol")
    visa: VISAConfig = Field(default_factory=VISAConfig)

class PGXLConfig(BaseModel):
    host: str = Field(...)
    port: int = Field(9007)
    model: str = Field("PGXL")

class FlexConfig(BaseModel):
    host: str = Field(..., description="Flex radio IP/hostname")
    port: int = Field(4992, description="TCP CAT/SmartSDR port")

class AppConfig(BaseModel):
    vna: VNAConfig = Field(default_factory=VNAConfig)
    pgxl: PGXLConfig
    flex: Optional[FlexConfig] = None
    bands_m: List[int] = Field(default_factory=lambda: [160,80,60,40,30,20,17,15,12,10,6])

def load_config(path: str) -> AppConfig:
    data = yaml.safe_load(pathlib.Path(path).read_text())
    return AppConfig.model_validate(data)
