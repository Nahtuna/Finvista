# -*- coding: utf-8 -*-
"""
🏆 FINVISTA: ATC (END-OF-SESSION CLOSE PRICE) DATA MANAGER MODULE
=================================================================
Module quản lý dữ liệu giá chốt phiên ATC:
  - Tự động sync dữ liệu ATC theo lịch trình (15:15 T2-T6)
  - Kiểm tra tính tươi mới của dữ liệu lúc App Startup
  - Trigger sync tự động khi dữ liệu thiếu / cũ
  - Theo dõi log trạng thái sync và độ tươi dữ liệu

Author: samvo
Version: 1.0
"""
