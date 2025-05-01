from io import BytesIO

import pandas as pd
from ..schemas import ExtractionResult


def to_xlsx_bytes(result: ExtractionResult) -> bytes:
    data = [row.model_dump() for row in result.rows]
    df = pd.DataFrame(data)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return buffer.getvalue() 