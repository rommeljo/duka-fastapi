from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm,HTTPBearer,HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
import jwt
import logging
from typing import Annotated
from fastapi import Depends, HTTPException, status




security=HTTPBearer()

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"


#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login",scheme_name="Bearer")
def create_access_token(email: str,SECRET_KEY=SECRET_KEY,ALGORITHM=ALGORITHM):
   
    encoded_jwt = jwt.encode({"email":email}, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        print("Token is >>>>>>>>>>>>>",token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        print("EMAIL is >>>>>>>>>>>>>",email)
        if email is None:
            raise credentials_exception
        return email
    except InvalidTokenError:
        raise credentials_exception
    
#async def get_current_active_user(
    ##current_user: Annotated[str, Depends(get_current_user)],
#):
   # if current_user.disabled:
        #raise HTTPException(status_code=400, detail="Inactive user")
    #return current_user

async def get_current_active_user(
    current_user: Annotated[str, Depends(get_current_user)],
):
    return current_user  
