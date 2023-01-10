import os

import requests
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view
import json
from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from urllib.parse import quote_plus, urlencode
import jwt

oauth = OAuth()

oauth.register(
    "auth0",
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f"https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration",
)


# Create your views here.
def check_user(request):
    user = request.headers.get('X-User-Name')
    if user is not None:
        return user
    else:
        return False


@api_view(['GET'])
def flights_list(request):
    token = oauth.auth0.authorize_access_token(request)
    if token['userinfo']:
        flights = requests.get(
            'http://' + os.environ.get('FLIGHT', 'localhost') + ':8060/api/v1/flights?page={}&size={}'.format(
                request.GET.get('page')
                , request.GET.get('size')))
        f = flights.json().append({'token': token})
        f.append({'token': token})
        return JsonResponse(flights.json(), status=flights.status_code, safe=False)
    return JsonResponse({'message': 'unauthorized'}, status=status.HTTP_401_UNAUTHORIZED, safe=False)


@api_view(['GET'])
def user_info(request):
    token = oauth.auth0.authorize_access_token(request)
    if token['userinfo']:
        user = json.dumps(token['userinfo'])
        tickets = requests.get('http://' + os.environ.get('TICKET', 'localhost') + ':8070/api/v1/user_tickets'
                               , headers={'X-User-Name': f'{user}'})
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
                                , headers={'X-User-Name': f'{user}'})
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
    return JsonResponse({'message': 'unauthorized'}, status=status.HTTP_401_UNAUTHORIZED, safe=False)


@api_view(['GET'])
def privilege_info(request):
    token = oauth.auth0.authorize_access_token(request)
    if token['userinfo']:
        user = json.dumps(token['userinfo'])
        info = requests.get("http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/balance_and_history"
                            , headers={'X-User-Name': f'{user}'})
        if info.status_code == 200:
            return JsonResponse(info.json(), status=status.HTTP_200_OK, safe=False)
        return JsonResponse(info.json(), status=info.status_code, safe=False)
    return JsonResponse({'message': 'unauthorized'}, status=status.HTTP_401_UNAUTHORIZED, safe=False)


@api_view(['GET', 'POST'])
def user_tickets_or_buy(request):
    user = check_user(request)
    if user:
        if request.method == 'GET':
            user_tickets = requests.get("http://" + os.environ.get('TICKET', 'localhost') + ":8070/api/v1/user_tickets"
                                        , headers={'X-User-Name': f'{user}'})
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
                                   headers={'X-User-Name': f'{user}'})
            if ticket.status_code != 201:
                return JsonResponse(ticket.json(), status=ticket.status_code, safe=False)
            count_bonus = requests.patch("http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/count_bonuses"
                                         , data={
                    "paidFromBalance": request.data["paidFromBalance"],
                    "price": request.data["price"],
                    "ticketUid": ticket.json()["ticketUid"]
                }
                                         , headers={'X-User-Name': f'{user}'})

            if count_bonus.status_code != 200:
                return JsonResponse(count_bonus.json(), status=count_bonus.status_code, safe=False)
            data = {}
            data.update(flight.json())
            data.update(ticket.json())
            data.update(count_bonus.json())
            return JsonResponse(data, status=status.HTTP_200_OK, safe=False)
    return JsonResponse({'message': 'user is necessary'}, status=status.HTTP_400_BAD_REQUEST, safe=False)


@api_view(['GET', 'DELETE'])
def user_ticket_info_or_cancel(request, ticketId):
    user = check_user(request)
    if user:
        if request.method == 'GET':
            user_ticket = requests.get(
                "http://" + os.environ.get('TICKET', 'localhost') + ":8070/api/v1/one_ticket_info/{}".format(ticketId)
                , headers={'X-User-Name': f'{user}'})
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
                , headers={'X-User-Name': f'{user}'})
            if ret_ticket.status_code != 204:
                return JsonResponse({'message': 'can\'t cancel ticket'}, status=status.HTTP_400_BAD_REQUEST, safe=False)
            turn_bonus = requests.patch(
                "http://" + os.environ.get('BONUS', 'localhost') + ":8050/api/v1/count_bonuses_from_return/{}".format(
                    ticketId)
                , headers={'X-User-Name': f'{user}'})
            if turn_bonus.status_code != 200:
                return JsonResponse({'message': 'can\'t count bonus'}, status=status.HTTP_400_BAD_REQUEST, safe=False)
            return JsonResponse({'message': 'Ticket successfully cancelled'}, status=status.HTTP_204_NO_CONTENT
                                , safe=False)
    return JsonResponse({'message': 'user is necessary'}, status=status.HTTP_400_BAD_REQUEST, safe=False)


def login(request):
    return oauth.auth0.authorize_redirect(
        request, request.build_absolute_uri(reverse("callback"))
    )


def callback(request):
    token = oauth.auth0.authorize_access_token(request)
    request.session["user"] = token
    return redirect(request.build_absolute_uri(reverse("index")))


def logout(request):
    request.session.clear()

    return redirect(
        f"https://{settings.AUTH0_DOMAIN}/v2/logout?"
        + urlencode(
            {
                "returnTo": request.build_absolute_uri(reverse("index")),
                "client_id": settings.AUTH0_CLIENT_ID,
            },
            quote_via=quote_plus,
        ),
    )
