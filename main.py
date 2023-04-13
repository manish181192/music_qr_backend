from fastapi import FastAPI, File, UploadFile, Response
import uvicorn
import os, io
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from PIL import Image
import cryptography.fernet as f
import qrcode
from asyncpg import Connection, Pool
from database import save_file_to_disk, save_file_to_db, connect_to_db, close_db_connection, get_db_connection
import uuid

app = FastAPI()

# Generate a 32-byte secret key
key = f.Fernet.generate_key()
# Store the key as an environment variable
os.environ['SECRET_KEY'] = key.decode()

MUSIC_STORAGE = '/Users/manish/Development/music_qr/music_qr_backend/uploads'
# security = HTTPBearer()
# Authorized users
# AUTHORIZED_USERS = ["user1", "user2"]

@app.on_event("startup")
async def startup_event():
    await connect_to_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_connection()

# Define a function to check if a user is authorized
# async def is_authorized(username: str = Depends(security)):
#     try:
#         payload = jwt.decode(username, SECRET_KEY, algorithms=["HS256"])
#         if payload["sub"] not in AUTHORIZED_USERS:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="Not authorized",
#             )
#     except jwt.exceptions.DecodeError:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Could not decode token",
#         )

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), db: Connection = Depends(get_db_connection)):
    music_id = str(uuid.uuid4())
    file_name = file.filename
    file_path = os.path.join(MUSIC_STORAGE, file_name)

    await save_file_to_disk(file_path, await file.read())
    await save_file_to_db(db, music_id, file_name, file_path)
    print(f"Saving music {file_name} with music_id: {music_id}")
    return JSONResponse(content={'music_id' : music_id, "message": "File uploaded successfully"})


@app.get("/get_music_id")
async def get_music_id(music_name: str, imei: str, db:Connection = Depends(get_db_connection)):
    query = "SELECT id FROM music WHERE imei = $1 AND music_name = $2;"
    music_id = await db.fetchval(query, imei, music_name, column="id")
    if music_id is None:
        raise HTTPException(status_code=404, detail="The music Id is not found, generate the QR code again!")
    return JSONResponse(content={'music_id': str(music_id)})


@app.get("/download/{music_id}/{action}", name="download")
async def download_file(music_id: str, action: str, db: Connection = Depends(get_db_connection)) -> StreamingResponse:
    query = "SELECT music_name, file_path FROM music WHERE id = $1;"
    file_path = await db.fetchval(query, music_id, column='file_path')
    music_name = await db.fetchval(query, music_id, column='music_name')
    if file_path is None or music_name is None:
        raise HTTPException(status_code=404, detail="File not found")

    if action == "stream":
        file_like = io.BytesIO(open(file_path, 'rb'))
        headers = {
                "Content-Disposition": f"inline; filename={music_name}", # specify filename
                "Accept-Ranges": "bytes",  # enable byte-range requests
                "Content-Type": "audio/mpeg", # specify MIME type
            }
        return StreamingResponse(file_like, media_type="audio/mpeg", headers=headers)
    elif action == "download":
        headers={"Content-Disposition": f"attachment; filename={music_name}"}
        return FileResponse(file_path, media_type="audio/mpeg", headers=headers)
    else:
        raise HTTPException(status_code=400, detail="Invalid action specified")


@app.post("/generate_qr_code")
async def generate_qr_code(
    request: Request,
    music_id: str,
    db: Connection = Depends(get_db_connection),
    # username: HTTPAuthorizationCredentials = Depends(is_authorized)
):
    query = "SELECT music_name, file_path FROM music WHERE id = $1;"
    file_path = await db.fetchval(query, music_id, column='file_path')
    music_name = await db.fetchval(query, music_id, column='music_name')
    download_url = request.url_for("download", music_id=music_id, action="download")

    if file_path is None or music_name is None:
        raise HTTPException(status_code=404, detail="File Not found")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # # Encrypt the UUID using Fernet and the secret key
    # key = os.environ['SECRET_KEY'].encode()
    # fernet = f.Fernet(key=key)
    # encrypted_uuid = fernet.encrypt(music_id.encode()).decode()
    
    # Generate the QR code using the encrypted UUID
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(download_url)
    qr.make(fit=False)
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the QR code image to a BytesIO object
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)

    # Return the QR code image as a response
    return StreamingResponse(img_byte_arr, media_type="image/png")



# @app.post("/recognize_qr_code")
# async def recognize_qr_code(
#     image: bytes,
#     db: Connection = Depends(get_db_connection),
#     # username: HTTPAuthorizationCredentials = Depends(is_authorized)
# ):
#     # Decode the QR code from the image
#     qr = qrcode.QRCode(version=1, box_size=10, border=5)
#     qr.add_data(image)
#     qr.make(fit=True)
#     encrypted_uuid = qr.data.decode()

#     # Decrypt the UUID using Fernet and the secret key
#     key = os.environ['SECRET_KEY'].encode()
#     fernet = f.Fernet(key)
#     music_id = fernet.decrypt(encrypted_uuid.encode()).decode()

#     # Retrieve the music file from the database using the UUID
#     query = "SELECT filename FROM music WHERE uuid = $1"
#     row = await db.fetch_one(query, music_id)
#     if row is None:
#         raise HTTPException(status_code=404, detail="File not found")
#     music_file = row["filename"]

#     # Open the music file and return it as a response
#     file_path = os.path.join(MUSIC_STORAGE, music_file)
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")
#     with open(file_path, "rb") as f:
#         contents = f.read()
#     return StreamingResponse(io.BytesIO(contents), media_type="audio/mpeg")



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8088,reload=True)