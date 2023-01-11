from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from .models import Ticket
from .serializers import TicketSerializer
import jwt
from authlib.integrations.django_oauth2 import ResourceProtector
from . import validator

require_auth = ResourceProtector()
validator = validator.Auth0JWTBearerTokenValidator(
    settings.AUTH0_DOMAIN,
    settings.AUTH0_AUDIENCE
)
require_auth.register_token_validator(validator)


def get_user_from_token(request):
    token = request.META.get('HTTP_AUTHORIZATION')
    user = jwt.decode(token[7:], options={"verify_signature": False})['sub']
    return user


# Create your views here.
@api_view(['GET'])
@require_auth(None)
def user_tickets(request):
    user = get_user_from_token(request)
    tickets = Ticket.objects.filter(username=user)
    if tickets is not None:
        serializer = TicketSerializer(tickets, many=True)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
    else:
        return JsonResponse({'message': 'No tickets'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@require_auth(None)
def one_ticket_info(request, ticketId):
    user = get_user_from_token(request)
    try:
        ticket = Ticket.objects.get(username=user, ticket_uid=ticketId)
        serializer = TicketSerializer(ticket, many=False)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)
    except:
        return JsonResponse({'message': 'No ticket'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@require_auth(None)
def buy_ticket(request):
    user = get_user_from_token(request)
    try:
        data = {
            "username": user,
            "flight_number": request.data["flightNumber"],
            "price": request.data["price"],
            "status": Ticket.StatusType.P
        }
        serializer = TicketSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        s = serializer.save()
        data = {
            "ticketUid": s.ticket_uid,
            "flightNumber": s.flight_number,
            "price": s.price,
            "status": s.status
        }
        return JsonResponse(data, status=status.HTTP_201_CREATED, safe=False)
    except Exception as e:
        return JsonResponse({'message': '{}'.format(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@require_auth(None)
def cancel_ticket(request, ticketId):
    user = get_user_from_token(request)
    try:
        ticket = Ticket.objects.get(ticket_uid=ticketId, username=user)
        if ticket.status == 'PAID':
            ticket.status = 'CANCELED'
            ticket.save()
            return JsonResponse({'message': 'Ticket is successfully canceled'}, status=status.HTTP_204_NO_CONTENT)
        else:
            return JsonResponse({'message': 'Ticket is already canceled'}, status=status.HTTP_400_BAD_REQUEST)
    except:
        return JsonResponse({'message': 'No ticket'}, status=status.HTTP_404_NOT_FOUND)
