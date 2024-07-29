from django.shortcuts import render
from django.http import HttpResponse, JsonResponse

from vendor.models import Vendor


from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import simplejson as json

def get_or_set_current_location(request):
    if 'lat' in request.session:
        lat = request.session['lat']
        lng = request.session['lng']
        return lng, lat
    elif 'lat' in request.GET:
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        request.session['lat'] = lat
        request.session['lng'] = lng
        return lng, lat
    else:
        return None

def home(request):
    if get_or_set_current_location(request) is not None:
        
        pnt = GEOSGeometry('POINT(%s  %s)' %(get_or_set_current_location(request)))
        vendors = Vendor.objects.filter(userProfile__location__distance_lte=(pnt, D(km=10000))
        ).annotate(distance=Distance("userProfile__location", pnt)).order_by("distance")
    
        for v in vendors:
            v.kms =  round(v.distance.km, 1)

    else:
        vendors = Vendor.objects.filter(is_approved=True, user__is_active=True)[:8]
    context = {
        'vendors':vendors,
    }
    return render(request, 'home.html', context)



@csrf_exempt
@require_POST
def callbackurl(request):
    try:
        # Parse the JSON data posted to the callback URL
        mpesa_response = json.loads(request.body)

        # Log the response to a file
        log_file = "M_PESAConfirmationResponse.txt"
        with open(log_file, "a") as log:
            log.write(json.dumps(mpesa_response) + "\n")

        print(mpesa_response)

        # Extract the ResultCode
        # result_code = mpesa_response['Body']['stkCallback']['ResultCode']
        #
        # if result_code == 0:
        #     # Extract additional information from the CallbackMetadata
        #     callback_metadata = mpesa_response['Body']['stkCallback']['CallbackMetadata']['Item']
        #
        #     # Initialize variables to store the extracted data
        #     mpesa_receipt_number = transaction_date = phone_number = amount = None
        #
        #     # Iterate through the metadata to extract the required fields
        #     for item in callback_metadata:
        #         if item['Name'] == 'MpesaReceiptNumber':
        #             mpesa_receipt_number = item['Value']
        #         elif item['Name'] == 'TransactionDate':
        #             transaction_date = item['Value']
        #         elif item['Name'] == 'PhoneNumber':
        #             phone_number = item['Value']
        #         elif item['Name'] == 'Amount':
        #             amount = item['Value']
        #
        #     # Print the extracted values
        #     print("MpesaReceiptNumber:", mpesa_receipt_number)
        #     print("TransactionDate:", transaction_date)
        #     print("PhoneNumber:", phone_number)
        #     print("Amount:", amount)
        #
        #     # Return the success response
        #     response = {
        #         "ResultCode": 0,
        #         "ResultDesc": "Confirmation Received Successfully"
        #     }
        #     print(response)

        #     return JsonResponse({"message": "Response received"}, status=200)
        # else:
        #     # Return a response indicating that the transaction failed
        #     response = {
        #         "ResultCode": result_code,
        #         "ResultDesc": "Transaction failed"
        #     }
        #     print(response)
        #     return JsonResponse(response, status=400)
        return JsonResponse({"message": "Response received"}, status=200)

    except json.JSONDecodeError:
        print("Invalid JSON data")
        return JsonResponse({"message": "Invalid JSON data"}, status=400)
    except KeyError as e:
        print(f"Missing key in JSON data: {e}")
        return JsonResponse({"message": f"Missing key in JSON data: {e}"}, status=400)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)
 