from flask import Flask, request, jsonify, send_from_directory
import threading
import asyncio
import edge_tts
import os
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio_files")
os.makedirs(AUDIO_DIR, exist_ok=True)

# НОВИ ПРОМЕНЛИВИ ЗА ОПАШКАТА
queue_lock = threading.Lock()
pending_items = []
worker_running = False

async def generate_single(item):
    idx = item['index']
    text = item['text']
    filename = os.path.join(AUDIO_DIR, f"{idx}.mp3")
    
    if not os.path.exists(filename) and text.strip():
        try:
            print(f"▶️ Генериране: [{idx}] {text[:50]}...")
            communicate = edge_tts.Communicate(text, "bg-BG-BorislavNeural")
            await communicate.save(filename)
        except Exception as e:
            print(f"❌ Грешка при [{idx}]: {e}")

# Работникът, който тегли файловете един по един
def worker_thread():
    global worker_running, pending_items
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        item_to_process = None
        # Взимаме НАЙ-ПРИОРИТЕТНАТА реплика
        with queue_lock:
            if len(pending_items) > 0:
                item_to_process = pending_items.pop(0)
            else:
                worker_running = False
                break
        
        if item_to_process:
            loop.run_until_complete(generate_single(item_to_process))
            
    loop.close()

@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/audio_files/<path:filename>')
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/generate', methods=['POST'])
def generate():
    global pending_items, worker_running
    data = request.json
    
    with queue_lock:
        pending_items = data.copy()
        if not worker_running:
            worker_running = True
            threading.Thread(target=worker_thread, daemon=True).start()
            
    return jsonify({"status": "OK"})

# НОВАТА КОМАНДА ЗА СМЯНА НА ПРИОРИТЕТИТЕ!
@app.route('/prioritize', methods=['POST'])
def prioritize():
    global pending_items
    target_idx = request.json.get('index', 0)
    
    print(f"\n⏩ ПРЕВЪРТАНЕ ЗАСЕЧЕНО! Сменям приоритета на реплика: [{target_idx}]\n")
    
    with queue_lock:
        # МАГИЯТА: Пренареждаме опашката! 
        # Всички реплики ОТ текущата нататък отиват НАЙ-ОТПРЕД. 
        # Старите (пропуснати) отиват най-отзад.
        pending_items.sort(key=lambda x: (x['index'] < target_idx, x['index']))
        
    return jsonify({"status": "Приоритетът е сменен!"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 СЪРВЪРЪТ РАБОТИ (С Умна Опашка!)")
    print("👉 ОТВОРИ БРАУЗЪРА СИ И ВЛЕЗ НА АДРЕС: http://localhost:5000")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=10000)
