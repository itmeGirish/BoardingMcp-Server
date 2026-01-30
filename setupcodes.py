# source .venv/bin/activate

#  python3 -m mcp_servers.boarding_mcp.onboardserver

#pytest tests/fixtures/directapiserver.py

#test
#pytest tests/fixtures/directapiserver.py::test_list_tools --inline-snapshot=create

# docker-compose -f docker-database-config.yml up -d




# === Result ===
# {
#   "success": true,
#   "data": {
#     "id": "2649029682146901",
#     "status": "PENDING",
#     "category": "UTILITY"
#   }
# }


#  [
#       {
#         "type": "BODY",
#         "text": "Hi {{1}}, your order {{2}} has been confirmed! It will be delivered by {{3}}. Total amount is {{4}}. Thank you for shopping with us.",
#         "example": {
#           "body_text": [
#             [
#               "Rahul",
#               "ORD12345",
#               "Feb 5, 2026",
#               "Rs 2,499"
#             ]
#           ]
#         }
#       },
#       {
#         "type": "FOOTER",
#         "text": "We appreciate your business"
#       },
#       {
#         "type": "BUTTONS",
#         "buttons": [
#           {
#             "type": "URL",
#             "text": "Track Order",
#             "url": "https://yourstore.com/track/{{1}}",
#             "example": [
#               "https://yourstore.com/track/ORD12345"
#             ]
#           },
#           {
#             "type": "PHONE_NUMBER",
#             "text": "Contact Support",
#             "phone_number": "+918861832522"
#           }
#         ]
#       }
#     ]