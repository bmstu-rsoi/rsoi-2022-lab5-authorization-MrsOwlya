import os
import requests
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
from django.conf import settings
import jwt
from authlib.integrations.django_oauth2 import ResourceProtector
from . import validator

require_auth = ResourceProtector()
validator = validator.Auth0JWTBearerTokenValidator(
    settings.AUTH0_DOMAIN,
    settings.AUTH0_AUDIENCE
)
require_auth.register_token_validator(validator)


# Create your views here.
def check_user(request):
    user = request.headers.get('X-User-Name')
    if user is not None:
        return user
    else:
        return False


def get_user_from_token(request):
    token = request.META.get('HTTP_AUTHORIZATION')
    user = jwt.decode(token[7:], options={"verify_signature": False})['sub']
    print(user)
    return user


@api_view(['GET'])
@require_auth(None)
def flights_list(request):
    flights = requests.get(
        'http://' + os.environ.get('FLIGHT', 'localhost') + ':8060/api/v1/flights?page={}&size={}'.format(
            request.GET.get('page')
            , request.GET.get('size')), headers={'Authorization': request.headers.get('Authorization')})
    return JsonResponse(flights.json(), status=flights.status_code, safe=False)


@api_view(['GET'])
@require_auth(None)
def user_info(request):
    tickets = requests.get('http://' + os.environ.get('TICKET', 'localhost') + ':8070/api/v1/user_tickets'
                           , headers={'Authorization': request.headers.get('Authorization')})
    if tickets.status_code == 200:
        tickets = tickets.json()
        ts = []
        for t in tickets:
            fl = requests.get('http://' + os.environ.get('FLIGHT', 'localhost') + ':8060/api/v1/flights/{}'.format(
                t['flight_number']))
            if fl.status_code == 200:
                fl = fl.json()
                data = {
                    "ticketUid": t['ticket_uid'],
                    "flightNumber": t['flight_number'],
                    "fromAirport": fl['fromAirport'],
                    "toAirport": fl['toAirport'],
                    "date": fl['date'],
                    "price": fl['price'],
                    "status": t['status']
                }
                ts.append(data)
        info = requests.get("http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/user_info"
                            , headers={'Authorization': request.headers.get('Authorization')})
        if info.status_code == 200:
            info = info.json()
            data = {
                "tickets": ts,
                "privilege": {
                    "balance": info['balance'],
                    "status": info['status']
                }
            }
            return JsonResponse(data, status=status.HTTP_200_OK, safe=False)
        return JsonResponse(info.json(), status=info.status_code)
    return JsonResponse(tickets.json(), status=tickets.status_code)


@api_view(['GET'])
@require_auth(None)
def privilege_info(request):
    info = requests.get("http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/balance_and_history"
                        , headers={'Authorization': request.headers.get('Authorization')})
    if info.status_code == 200:
        return JsonResponse(info.json(), status=status.HTTP_200_OK, safe=False)
    return JsonResponse(info.json(), status=info.status_code, safe=False)


@api_view(['GET', 'POST'])
@require_auth(None)
def user_tickets_or_buy(request):
    if request.method == 'GET':
        user_tickets = requests.get("http://" + os.environ.get('TICKET', 'localhost') + ":8070/api/v1/user_tickets"
                                    , headers={'Authorization': request.headers.get('Authorization')})
        if user_tickets.status_code == 200:
            user_tickets = user_tickets.json()
            ts = []
            for t in user_tickets:
                fl = requests.get(
                    "http://" + os.environ.get('FLIGHT', 'localhost') + ":8060/api/v1/flights/{}".format(
                        t['flight_number']))
                if fl.status_code == 200:
                    fl = fl.json()
                    data = {
                        "ticketUid": t['ticket_uid'],
                        "flightNumber": t['flight_number'],
                        "fromAirport": fl['fromAirport'],
                        "toAirport": fl['toAirport'],
                        "date": fl['date'],
                        "price": fl['price'],
                        "status": t['status']
                    }
                    ts.append(data)
            return JsonResponse(ts, status=status.HTTP_200_OK, safe=False)
        return JsonResponse(user_tickets.json(), status=user_tickets.status_code, safe=False)
    if request.method == 'POST':
        flight = requests.get("http://" + os.environ.get('FLIGHT', 'localhost') + ":8060/api/v1/flights/{}".format(
            request.data["flightNumber"]))
        if flight.status_code != 200 or int(flight.json()['price']) != int(request.data["price"]):
            return JsonResponse({'message': 'no flight'}, status=status.HTTP_404_NOT_FOUND, safe=False)
        ticket = requests.post("http://" + os.environ.get('TICKET', 'localhost') + ":8070/api/v1/buy_ticket",
                               data=request.data,
                               headers={'Authorization': request.headers.get('Authorization')})
        if ticket.status_code != 201:
            return JsonResponse(ticket.json(), status=ticket.status_code, safe=False)
        count_bonus = requests.patch("http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/count_bonuses"
                                     , data={
                "paidFromBalance": request.data["paidFromBalance"],
                "price": request.data["price"],
                "ticketUid": ticket.json()["ticketUid"]
            }
                                     , headers={'Authorization': request.headers.get('Authorization')})

        if count_bonus.status_code != 200:
            return JsonResponse(count_bonus.json(), status=count_bonus.status_code, safe=False)
        data = {}
        data.update(flight.json())
        data.update(ticket.json())
        data.update(count_bonus.json())
        return JsonResponse(data, status=status.HTTP_200_OK, safe=False)


@api_view(['GET', 'DELETE'])
@require_auth(None)
def user_ticket_info_or_cancel(request, ticketId):
    if request.method == 'GET':
        user_ticket = requests.get(
            "http://" + os.environ.get('TICKET', 'localhost') + ":8070/api/v1/one_ticket_info/{}".format(ticketId)
            , headers={'Authorization': request.headers.get('Authorization')})
        if user_ticket.status_code == 200:
            user_ticket = user_ticket.json()
            fl = requests.get("http://" + os.environ.get('FLIGHT', 'localhost') + ":8060/api/v1/flights/{}".format(
                user_ticket['flight_number']))
            if fl.status_code == 200:
                fl = fl.json()
                data = {
                    "ticketUid": user_ticket['ticket_uid'],
                    "flightNumber": user_ticket['flight_number'],
                    "fromAirport": fl['fromAirport'],
                    "toAirport": fl['toAirport'],
                    "date": fl['date'],
                    "price": fl['price'],
                    "status": user_ticket['status']
                }
                return JsonResponse(data, status=status.HTTP_200_OK, safe=False)
        return JsonResponse({'message': 'no ticket'}, status=status.HTTP_404_NOT_FOUND, safe=False)
    if request.method == 'DELETE':
        ret_ticket = requests.patch(
            "http://" + os.environ.get('TICKET', 'localhost') + ":8070/api/v1/cancel_ticket/{}".format(ticketId)
            , headers={'Authorization': request.headers.get('Authorization')})
        if ret_ticket.status_code != 204:
            return JsonResponse({'message': 'can\'t cancel ticket'}, status=status.HTTP_400_BAD_REQUEST, safe=False)
        turn_bonus = requests.patch(
            "http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/count_bonuses_from_return/{}".format(
                ticketId)
            , headers={'Authorization': request.headers.get('Authorization')})
        if turn_bonus.status_code != 200:
            return JsonResponse({'message': 'can\'t count bonus'}, status=status.HTTP_400_BAD_REQUEST, safe=False)
        return JsonResponse({'message': 'Ticket successfully cancelled'}, status=status.HTTP_204_NO_CONTENT
                            , safe=False)
