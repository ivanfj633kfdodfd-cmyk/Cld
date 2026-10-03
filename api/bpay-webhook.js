// api/bpay-webhook.js — принимает уведомления от B Pay
// Проверяет HMAC-SHA256 подпись, при успехе уведомляет юзера в Telegram

const crypto    = require('crypto');
const BOT_TOKEN = process.env.BOT_TOKEN;
const WH_SECRET = process.env.BPAY_WEBHOOK_SECRET;

async function notifyUser(chatId, orderId, amount) {
    const text =
        `✅ <b>Оплата получена!</b>\n\n` +
        `<b>Заказ #${orderId}</b> подтверждён.\n` +
        `<b>Сумма:</b> ${Number(amount).toLocaleString('ru-RU')} ₽\n\n` +
        `Твой заказ уже готовится. Спасибо!`;

    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            chat_id:    chatId,
            text,
            parse_mode: 'HTML'
        })
    });
}

async function notifyFailed(chatId, orderId) {
    const text =
        `❌ <b>Оплата не прошла</b>\n\n` +
        `Заказ #${orderId} отменён или истекло время оплаты.\n\n` +
        `Используй /order чтобы оформить новый заказ.`;

    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            chat_id:    chatId,
            text,
            parse_mode: 'HTML'
        })
    });
}

module.exports = async function handler(req, res) {
    if (req.method !== 'POST') return res.status(405).end();

    // Читаем сырое тело для проверки подписи
    // Vercel по умолчанию парсит JSON — нам нужна сырая строка
    // Используем трюк: сериализуем обратно (работает если Vercel не менял порядок ключей)
    const rawBody = JSON.stringify(req.body);

    // Проверяем подпись
    if (WH_SECRET) {
        const sigHeader = req.headers['x-betapay-signature'] || '';
        const [algo, receivedHex] = sigHeader.split('=');

        if (algo !== 'sha256' || !receivedHex) {
            console.warn('bpay-webhook: bad signature header');
            return res.status(400).end();
        }

        const expectedHex = crypto
            .createHmac('sha256', WH_SECRET)
            .update(rawBody)
            .digest('hex');

        // constant-time compare
        const a = Buffer.from(receivedHex, 'hex');
        const b = Buffer.from(expectedHex, 'hex');

        if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
            console.warn('bpay-webhook: signature mismatch');
            return res.status(401).end();
        }
    } else {
        console.warn('bpay-webhook: BPAY_WEBHOOK_SECRET не задан, подпись не проверяется!');
    }

    const { event, data } = req.body;

    console.log('bpay-webhook event:', event, data?.public_id);

    // Парсим order_id: формат pvz_{chatId}_{orderId}
    const orderId = data?.order_id || '';
    let chatId  = null;
    let shortId = orderId;

    if (orderId.startsWith('pvz_')) {
        const parts = orderId.split('_');
        // pvz _ chatId _ orderId
        if (parts.length >= 3) {
            chatId  = parts[1];
            shortId = parts[2];
        }
    }

    if (!chatId) {
        console.warn('bpay-webhook: не удалось извлечь chatId из order_id:', orderId);
        return res.status(200).end(); // всё равно отвечаем 200 чтобы B Pay не ретраил
    }

    try {
        if (event === 'payment.success') {
            await notifyUser(chatId, shortId, data.amount);
        } else if (event === 'payment.failed') {
            await notifyFailed(chatId, shortId);
        }
        // qr.ready, payout.* — игнорируем
    } catch (err) {
        console.error('bpay-webhook notify error:', err);
    }

    return res.status(200).end();
};
