"""MCP prompts — reusable prompt templates."""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base


def register(mcp: FastMCP) -> None:
    @mcp.prompt()
    def monthly_review(month: str | None = None) -> list[base.Message]:
        """Đánh giá tài chính tổng hợp cho một tháng."""
        m = month or "tháng hiện tại"
        return [
            base.UserMessage(
                f"Hãy đánh giá tài chính tháng {m} cho tôi. Bao gồm:\n"
                f"1. Tổng thu nhập, chi tiêu, tiết kiệm (so sánh với tháng trước)\n"
                f"2. Top 5 khoản chi lớn nhất\n"
                f"3. Chi tiêu theo danh mục (danh mục nào tăng/giảm)\n"
                f"4. Tình trạng ngân sách (có vượt không?)\n"
                f"5. Đánh giá chung và lời khuyên cải thiện\n\n"
                f"Sử dụng các tool: get_financial_summary, get_spending_by_category, "
                f"get_top_expenses, get_budget_status để lấy dữ liệu."
            )
        ]

    @mcp.prompt()
    def budget_advice() -> list[base.Message]:
        """Tư vấn phân bổ ngân sách dựa trên chi tiêu thực tế."""
        return [
            base.UserMessage(
                "Phân tích chi tiêu 3 tháng gần nhất và tư vấn ngân sách cho tôi:\n"
                "1. Xu hướng chi tiêu theo danh mục qua các tháng\n"
                "2. Danh mục nào đang chi quá nhiều?\n"
                "3. Đề xuất ngân sách hợp lý theo quy tắc 50/30/20\n"
                "4. Cách cắt giảm chi tiêu không cần thiết\n\n"
                "Sử dụng các tool: get_spending_trends, get_spending_by_category, "
                "get_financial_summary, get_budget_status."
            )
        ]

    @mcp.prompt()
    def goal_planning(goal_name: str | None = None) -> list[base.Message]:
        """Lập kế hoạch đạt mục tiêu tài chính."""
        target = f"mục tiêu '{goal_name}'" if goal_name else "các mục tiêu"
        return [
            base.UserMessage(
                f"Hãy giúp tôi lập kế hoạch đạt {target}:\n"
                f"1. Tiến độ hiện tại của từng mục tiêu\n"
                f"2. Số tiền cần tiết kiệm mỗi tháng để đạt mục tiêu đúng hạn\n"
                f"3. Dựa trên thu nhập và chi tiêu hiện tại, liệu có khả thi không?\n"
                f"4. Đề xuất điều chỉnh nếu tiến độ chậm\n\n"
                f"Sử dụng các tool: get_goals, get_financial_summary."
            )
        ]

    @mcp.prompt()
    def investment_review() -> list[base.Message]:
        """Đánh giá danh mục đầu tư."""
        return [
            base.UserMessage(
                "Đánh giá danh mục đầu tư của tôi:\n"
                "1. Tổng quan portfolio: tổng giá trị, lãi/lỗ\n"
                "2. Phân bổ tài sản theo loại (cổ phiếu, vàng, crypto...)\n"
                "3. Khoản nào đang lãi/lỗ nhiều nhất?\n"
                "4. Đề xuất rebalance nếu cần\n\n"
                "Sử dụng các tool: get_portfolio, get_account_summary, get_financial_summary."
            )
        ]

    @mcp.prompt()
    def financial_health() -> list[base.Message]:
        """Kiểm tra sức khỏe tài chính tổng thể."""
        return [
            base.UserMessage(
                "Kiểm tra sức khỏe tài chính tổng thể của tôi:\n"
                "1. Tài sản ròng và phân bổ (tiền mặt, ngân hàng, đầu tư, nợ)\n"
                "2. Tỷ lệ tiết kiệm 3 tháng gần nhất\n"
                "3. Quỹ khẩn cấp có đủ 3-6 tháng chi tiêu không?\n"
                "4. Tỷ lệ nợ/tài sản\n"
                "5. Tiến độ các mục tiêu tài chính\n"
                "6. Hóa đơn sắp tới cần thanh toán\n"
                "7. Đánh giá tổng thể và khuyến nghị\n\n"
                "Sử dụng tất cả các tool cần thiết để có bức tranh đầy đủ."
            )
        ]
