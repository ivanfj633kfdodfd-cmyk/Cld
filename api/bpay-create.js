// api/bpay-create.js — создаёт платёж через B Pay API
// Токен скрыт на сервере, во фронтенд не попадает

const BPAY_API_KEY  = process.env.BPAY_API_KEY;
const BPAY_API_HOST = 'https://b-pay-provider.com/api/v1';

module.exports = async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Allow-Private-Network', 'true');
    res.setHeader('Vary', 'Origin');

    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'Method not allowed' });

    try {
        const { amount, orderId, chatId, description } = req.body;

        if (!amount || !orderId || !chatId) {
            return res.status(400).json({ ok: false, error: 'amount, orderId, chatId обязательны' });
        }

        if (!BPAY_API_KEY) {
            return res.status(500).json({ ok: false, error: 'BPAY_API_KEY не настроен в Vercel' });
        }

        // Кодируем chatId прямо в order_id — webhook потом распарсит
        // Формат: pvz_{chatId}_{orderId}
        const encodedOrderId = `pvz_${chatId}_${orderId}`;

        const bpayRes = await fetch(`${BPAY_API_HOST}/payment/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${BPAY_API_KEY}`,
                'Content-Type':  'application/json'
            },
            body: JSON.stringify({
                amount:      Number(amount),
                currency:    'RUB',
                order_id:    encodedOrderId,
                description: description || `Заказ #${orderId} — PvZ Shop`
            })
        });

        const data = await bpayRes.json();

        if (!data.ok) {
            console.error('B Pay error:', data);
            return res.status(502).json({ ok: false, error: data.error || 'Ошибка B Pay API' });
        }

        return res.status(200).json({
            ok:          true,
            payment_url: data.payment.payment_url,
            public_id:   data.payment.public_id,
            status:      data.payment.status
        });

    } catch (err) {
        console.error('bpay-create error:', err);
        return res.status(500).json({ ok: false, error: err.message });
    }
};
