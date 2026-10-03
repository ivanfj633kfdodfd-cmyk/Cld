// api/webhook.js — Telegram Bot webhook handler

const BOT_TOKEN = process.env.BOT_TOKEN;

async function sendMessage(chatId, text, extra = {}) {
    const body = { chat_id: chatId, text, parse_mode: 'HTML', ...extra };
    const res = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    return res.json();
}

module.exports = async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(200).json({ ok: true, info: 'Bot is running' });
    }

    try {
        const update = req.body;

        if (update.message) {
            const msg = update.message;
            const chatId = msg.chat.id;
            const text = msg.text || '';

            if (text === '/start') {
                // Отправляем картинку с красивым текстом
                await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        chat_id: chatId,
                        photo: 'https://github.com/HuntersNetPlus/PvZ/blob/main/AV_1-ezgif.com-video-to-webp-converter.webp?raw=true',
                        caption:
                            `<b>Добро пожаловать в PvZ Shop</b>\n\n` +
                            `<blockquote>Быстро, анонимно и круглосуточно.\n` +
                            `Работаем без выходных — твой заказ всегда под рукой.</blockquote>\n\n` +
                            `Широкий ассортимент, актуальные цены и мгновенное оформление прямо в Telegram.\n\n` +
                            `👇`,
                        parse_mode: 'HTML',
                        reply_markup: {
                            inline_keyboard: [[
                                {
                                    text: 'Открыть витрину',
                                    web_app: { url: 'https://pvz-pink.vercel.app/index.html' }
                                }
                            ]]
                        }
                    })
                });

            } else if (text === '/order') {
                await sendMessage(chatId,
                    'Форма создания заказа.\n\nЗаполни все поля и нажми "Сформировать заказ".',
                    {
                        reply_markup: {
                            inline_keyboard: [[
                                {
                                    text: 'Создать заказ',
                                    web_app: { url: 'https://pvz-pink.vercel.app/order.html' }
                                }
                            ]]
                        }
                    }
                );

            } else if (text === '/list') {
                await sendMessage(chatId,
                    '<b>Прямые ссылки PvZ Shop:</b>\n\n' +
                    '• <a href="https://t.me/pvz5bot/shop">Витрина</a> — t.me/pvz5bot/shop\n' +
                    '• <a href="https://t.me/pvz5bot/info">Инфо</a> — t.me/pvz5bot/info\n' +
                    '• <a href="https://t.me/pvz5bot/landingpage">Лендинг</a> — t.me/pvz5bot/landingpage\n' +
                    '• <a href="https://t.me/pvz5bot/panel">Панель</a> — t.me/pvz5bot/panel'
                );

            } else {
                await sendMessage(chatId, 'Используй /start чтобы открыть витрину.');
            }
        }

        return res.status(200).json({ ok: true });
    } catch (err) {
        console.error('Webhook error:', err);
        return res.status(200).json({ ok: false, error: err.message });
    }
}
