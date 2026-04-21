"""MCP prompts — quick-action templates for external MCP clients.

Exposed to Claude Desktop / MCP Inspector etc. Bodies describe the analysis
goal rather than hardcoding tool names, so they don't go stale when tools are
renamed or added. The agent picks the right tools from its schema.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base


def register(mcp: FastMCP) -> None:
    @mcp.prompt()
    def monthly_review(month: str | None = None) -> list[base.Message]:
        """Đánh giá tài chính tổng hợp cho một tháng."""
        m = month or "tháng hiện tại"
        return [
            base.UserMessage(
                f"Hãy đánh giá tài chính tháng {m}. Bao gồm:\n"
                "1. Tổng thu nhập, chi tiêu, tiết kiệm — so sánh với tháng trước.\n"
                "2. Top khoản chi lớn nhất.\n"
                "3. Chi tiêu theo danh mục (tăng/giảm so với tháng trước).\n"
                "4. Tình trạng ngân sách (có vượt không, danh mục nào sát hạn mức).\n"
                "5. Đánh giá chung và lời khuyên cải thiện.\n\n"
                "Dùng các tool tài chính có sẵn để lấy số liệu thực, không bịa."
            )
        ]

    @mcp.prompt()
    def budget_advice() -> list[base.Message]:
        """Tư vấn phân bổ ngân sách dựa trên chi tiêu thực tế."""
        return [
            base.UserMessage(
                "Phân tích chi tiêu 3 tháng gần nhất và tư vấn ngân sách:\n"
                "1. Xu hướng chi tiêu theo danh mục qua các tháng.\n"
                "2. Danh mục đang chi quá nhiều so với tỷ lệ hợp lý.\n"
                "3. Đề xuất ngân sách theo quy tắc 50/30/20 (nhu cầu/mong muốn/tiết kiệm).\n"
                "4. Cách cắt giảm chi tiêu không cần thiết."
            )
        ]

    @mcp.prompt()
    def goal_planning(goal_name: str | None = None) -> list[base.Message]:
        """Lập kế hoạch đạt mục tiêu tài chính."""
        target = f"mục tiêu '{goal_name}'" if goal_name else "các mục tiêu"
        return [
            base.UserMessage(
                f"Giúp tôi lập kế hoạch đạt {target}:\n"
                "1. Tiến độ hiện tại của từng mục tiêu.\n"
                "2. Số tiền cần tiết kiệm mỗi tháng để đạt đúng hạn.\n"
                "3. Dựa trên thu nhập/chi tiêu hiện tại — có khả thi không?\n"
                "4. Đề xuất điều chỉnh nếu tiến độ chậm."
            )
        ]

    @mcp.prompt()
    def investment_review() -> list[base.Message]:
        """Đánh giá danh mục đầu tư."""
        return [
            base.UserMessage(
                "Đánh giá danh mục đầu tư của tôi:\n"
                "1. Tổng quan portfolio: tổng giá trị, lãi/lỗ.\n"
                "2. Phân bổ tài sản theo loại (cổ phiếu, vàng, crypto...).\n"
                "3. Khoản đang lãi/lỗ nhiều nhất.\n"
                "4. Đề xuất rebalance nếu cần (mức tập trung quá cao ở 1 loại)."
            )
        ]

    @mcp.prompt()
    def financial_health() -> list[base.Message]:
        """Kiểm tra sức khỏe tài chính tổng thể."""
        return [
            base.UserMessage(
                "Kiểm tra sức khỏe tài chính tổng thể:\n"
                "1. Tài sản ròng và phân bổ (tiền mặt, ngân hàng, đầu tư, nợ).\n"
                "2. Tỷ lệ tiết kiệm 3 tháng gần nhất.\n"
                "3. Quỹ khẩn cấp có đủ 3-6 tháng chi tiêu không?\n"
                "4. Tỷ lệ nợ/tài sản.\n"
                "5. Tiến độ các mục tiêu tài chính.\n"
                "6. Hóa đơn sắp tới cần thanh toán.\n"
                "7. Đánh giá tổng thể và khuyến nghị ưu tiên."
            )
        ]
