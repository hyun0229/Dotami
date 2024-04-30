from flask import Flask,request,jsonify
import boto3
import base64
import mysql.connector
from datetime import datetime

app = Flask(__name__)
s3 = boto3.client('s3')


db_config = {
    "host": "dotami",
    "user": "admin",
    "password": "pw",
    "database": "dotami"
}
def create_db_connection():
    return mysql.connector.connect(**db_config)


@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image_data' not in request.json:
        return jsonify({"error": "No image data found in JSON request"})
    
    date = request.json['date']
    location = request.json['location']
    uid = request.json['uid']
    base64_image = request.json['image_data']
    date_obj = datetime.strptime(date,"%Y-%m-%d %H:%M:%S")

    # Base64로 인코딩된 이미지 데이터 디코딩
    image_data = base64.b64decode(base64_image)
    
    # S3 버킷과 파일 이름 설정
    bucket_name = 'dotami-potehole-image'
    object_name = uid+date+'.png'
    
    try:
        # S3에 이미지 업로드
        s3.put_object(Bucket=bucket_name, Key=object_name, Body=image_data)
        
        # 업로드된 이미지의 URL 생성
        image_url = f"https://{bucket_name}.s3.amazonaws.com/{object_name}"

        connection = create_db_connection()
        cursor = connection.cursor()
        insert_query = "INSERT INTO PotholeReports (ReporterID, Location, DateReported, ImageUrl) VALUES (%s, %s, %s, %s)"
        values =(int(uid),location , date_obj,image_url)
        cursor.execute(insert_query, values)

        connection.commit()
        cursor.close()
        connection.close()
        
        response = {"message": "Image uploaded successfully", "image_url": image_url}
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/hi")
def index():
       return "Hello, World!"


@app.route('/get_pothole_reports', methods=['GET'])
def get_pothole_reports():
    try:
    
        connection = create_db_connection()
        cursor = connection.cursor(dictionary=True)
        select_query = "SELECT ReportID, DateReported, Location FROM PotholeReports"
        cursor.execute(select_query)
        reports = cursor.fetchall()
        cursor.close()
        connection.close()
        for report in reports:
            report['DateReported'] =str(report['DateReported'].isoformat())
            report['ReportID'] = str(report['ReportID'])
        return jsonify({"pothole_reports": reports})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/get_report', methods=['GET'])
def get_report():
    report_id = request.args.get('ReportID')

    try:
        connection = create_db_connection()
        cursor = connection.cursor(dictionary=True)
        select_query = "SELECT * FROM PotholeReports WHERE ReportID = %s"
        cursor.execute(select_query, (report_id,))
        report = cursor.fetchone()
        cursor.close()
        connection.close()

        if report:
            # 필요한 정보를 JSON 형식으로 응답
            response = {
                'ReportID': report['ReportID'],
                'ReporterID': report['ReporterID'],
                'DateReported': report['DateReported'].isoformat(),
                'Location': report['Location'],
                'ImageUrl': report['ImageUrl'],
                'Status': report['Status']
            }
            return jsonify(response)
        else:
            return jsonify({'error': 'Report not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/manage_favorite', methods=['POST'])
def manage_favorite():
    try:
        data = request.json
        uid = data.get('uid')
        report_id = data.get('report_id')

        if uid is None or report_id is None:
            return jsonify({"error": "Missing UID or ReportID in the request"})

        # Check if the entry exists
        connection = create_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Favorites WHERE Uid = %s AND ReportID = %s", (uid, report_id))
        existing_entry = cursor.fetchone()

        if existing_entry:
            # If the entry exists, remove it (unfavorite)
            cursor.execute("DELETE FROM Favorites WHERE Uid = %s AND ReportID = %s", (uid, report_id))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({"message": "Removed from favorites"})
        else:
            # If the entry does not exist, add it (favorite)
            cursor.execute("INSERT INTO Favorites (Uid, ReportID) VALUES (%s, %s)", (uid, report_id))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({"message": "Added to favorites"})

    except Exception as e:
        return jsonify({"error": str(e)})




@app.route('/get_favorites', methods=['GET'])
def get_favorites():
    try:
        uid = request.args.get('uid')

        if uid is None:
            return jsonify({"error": "Missing UID in the request"})

        connection = create_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT ReportID FROM Favorites WHERE Uid = %s", (uid,))
        favorite_reports = [row[0] for row in cursor.fetchall()]

        cursor.close()
        connection.close()

        return jsonify({"favorite_reports": favorite_reports})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)

