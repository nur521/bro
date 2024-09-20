import mysql.connector
from flask import Flask, request, jsonify

app = Flask(__name__)

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="n@1234mine@4321",
    database="tokens_db"
)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    tokens INT DEFAULT 0,
    referred_by BIGINT,
    referral_count INT DEFAULT 0,
    received_initial_tokens BOOLEAN DEFAULT 0,
    wallet_address VARCHAR(255)
)''')
conn.commit()

TOTAL_TOKENS = 100000000000  # Общее количество токенов для раздачи

@app.route('/login', methods=['POST'])
def login():
    user_id = request.json.get('user_id')
    username = request.json.get('username')

    # Проверяем, получил ли пользователь начальные токены
    cursor.execute("SELECT tokens, received_initial_tokens FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if user:
        tokens, received_initial_tokens = user
        if not received_initial_tokens:
            tokens += 1500
            cursor.execute("UPDATE users SET tokens = %s, received_initial_tokens = TRUE WHERE user_id = %s", (tokens, user_id))
            conn.commit()
        return jsonify({'tokens': tokens})
    else:
        # Создаем нового пользователя и даем ему 1500 токенов
        cursor.execute("INSERT INTO users (user_id, username, tokens, received_initial_tokens) VALUES (%s, %s, %s, %s)", (user_id, username, 1500, True))
        conn.commit()
        return jsonify({'tokens': 1500})

@app.route('/get_referrals', methods=['GET'])
def get_referrals():
    user_id = request.args.get('user_id')

    cursor.execute("SELECT referral_count FROM users WHERE user_id = %s", (user_id,))
    referral_count = cursor.fetchone()[0]

    cursor.execute("SELECT username, user_id FROM users WHERE referred_by = %s", (user_id,))
    referrals = cursor.fetchall()

    return jsonify({
        'referral_count': referral_count,
        'referrals': [{'username': ref[0], 'user_id': ref[1]} for ref in referrals]
    })

@app.route('/add_referral', methods=['POST'])
def add_referral():
    referrer_id = request.json.get('referrer_id')
    new_user_id = request.json.get('new_user_id')
    new_username = request.json.get('new_username')

    # Добавляем нового реферала
    cursor.execute("INSERT INTO users (user_id, username, referred_by) VALUES (%s, %s, %s)", (new_user_id, new_username, referrer_id))

    # Обновляем реферальные данные реферера
    cursor.execute("UPDATE users SET referral_count = referral_count + 1, tokens = tokens + 50 WHERE user_id = %s", (referrer_id,))
    
    # Проверяем, нужно ли начислить дополнительные 1500 токенов
    cursor.execute("SELECT referral_count, tokens FROM users WHERE user_id = %s", (referrer_id,))
    referral_count, tokens = cursor.fetchone()
    if referral_count == 5:
        tokens += 1500
        cursor.execute("UPDATE users SET tokens = %s WHERE user_id = %s", (tokens, referrer_id))
    
    conn.commit()
    return jsonify({'message': 'Referral added successfully'})

@app.route('/remaining_tokens', methods=['GET'])
def remaining_tokens():
    cursor.execute("SELECT SUM(tokens) FROM users")
    total_distributed_tokens = cursor.fetchone()[0]
    remaining_tokens = TOTAL_TOKENS - total_distributed_tokens

    return jsonify({'remaining_tokens': remaining_tokens})

if __name__ == '__main__':
    app.run(debug=True)
