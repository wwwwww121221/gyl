import asyncio
from pathlib import Path

from services.contract_service import generate_contract_pdf_from_mock_data


async def main():
    mock_data = {
        "supplier_name": "上海星河供应链有限公司",
        "project_no": "PRJ-2026-031",
        "contract_amount": 86500.00,
        "items": [
            {"index": 1, "material_name": "不锈钢管", "material_code": "MAT-001", "qty": 120, "price": 180.0, "amount": 21600.0},
            {"index": 2, "material_name": "法兰盘", "material_code": "MAT-002", "qty": 60, "price": 250.0, "amount": 15000.0},
            {"index": 3, "material_name": "高压阀门", "material_code": "MAT-003", "qty": 35, "price": 1425.71, "amount": 49899.85},
        ],
    }

    file_path = await generate_contract_pdf_from_mock_data(
        {
            "supplier_name": mock_data["supplier_name"],
            "project_no": mock_data["project_no"],
            "total_amount": mock_data["contract_amount"],
            "items": mock_data["items"],
            "task_title": "测试合同"
        },
        output_filename="test_result.pdf"
    )

    result_file = Path(file_path)
    if result_file.exists():
        print(str(result_file))


if __name__ == "__main__":
    asyncio.run(main())
