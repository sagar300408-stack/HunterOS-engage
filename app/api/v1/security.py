from fastapi import Request, HTTPException, status
from ipaddress import ip_address, ip_network
import logging

logger = logging.getLogger(__name__)

# Very basic internal network check for B1 boundary
def verify_internal_network(request: Request):
    client_ip = request.client.host if request.client else None
    if not client_ip:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown client IP")
        
    # Example allowed networks: localhost, docker networks, kubernetes pod CIDR
    allowed_networks = [
        ip_network("127.0.0.0/8"),
        ip_network("10.0.0.0/8"),
        ip_network("172.16.0.0/12"),
        ip_network("192.168.0.0/16"),
        ip_network("::1/128"),
    ]
    
    try:
        ip = ip_address(client_ip)
        if not any(ip in network for network in allowed_networks):
            logger.warning(f"Unauthorized external access attempt from {client_ip}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Internal network access required")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid IP address format")
        
    return client_ip
