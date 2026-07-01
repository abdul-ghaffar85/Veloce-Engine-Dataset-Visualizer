import asyncio
import pandas as pd
from backend.services.profiler import get_profiling_service
from backend.services.field_schema_engine import get_field_schema_engine
from backend.services.semantic_engine import get_semantic_engine

async def main():
    df = pd.DataFrame({
        "Country": ["USA", "Canada", "Mexico", "UK", "France", "Germany", "Japan", "USA"],
        "Product": ["A", "B", "C", "A", "B", "C", "A", "D"],
        "Sale Price": [10.5, 20.0, 15.0, 10.0, 30.5, 25.0, 50.0, 10.0],
        "Customer ID": [1, 2, 3, 4, 5, 6, 7, 8]
    })
    
    schema_engine = get_field_schema_engine()
    schema = await schema_engine.build_schema("test", "test.csv", df)
    
    for f in schema.fields:
        print(f"Field: {f.field}, SemanticType: {f.semanticType.value}, DataType: {f.dataType.value}")

if __name__ == "__main__":
    asyncio.run(main())
