// api/send.js — проксирует отправку заказа в Telegram

const BOT_TOKEN = process.env.BOT_TOKEN;

module.exports = async function handler(req, res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'Method not allowed' });

    try {
        const { chatId, orderId, location, product, price, payMethod, requisites, comment } = req.body;

        if (!chatId || !orderId) {
            return res.status(400).json({ ok: false, error: 'chatId и orderId обязательны' });
        }

        const reply_markup = {
            inline_keyboard: [[
                { text: '⏳ Ожидает оплаты', callback_data: 'status_pending' }
            ]]
        };

        // Пробуем sendRichMessage с таблицей (как в Claude Bot)
        const md =
            `# Новый заказ #${orderId}\n\n` +
            `| | |\n` +
            `| :--- | :--- |\n` +
            `| **Локация** | ${location || '—'} |\n` +
            `| **Позиция** | ${product || '—'} |\n` +
            `| **Сумма** | ${price || '—'} |\n` +
            `| **Оплата** | ${payMethod || '—'} |\n` +
            (comment ? `| **Комментарий** | ${comment} |\n` : '') +
            `\n**Реквизиты для оплаты:**\n\n` +
            `\`${requisites || '—'}\`\n\n` +
            `> После перевода нажмите кнопку ниже.`;

        const richRes = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendRichMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: chatId,
                rich_message: { markdown: md },
                reply_markup
            })
        });
        const richData = await richRes.json();

        // Если sendRichMessage сработал — отправляем ещё фото отдельно перед ним
        if (richData.ok) {
            // Шлём картинку первой (без текста)
            await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: chatId,
                    photo: 'https://github.com/HuntersNetPlus/PvZ/blob/main/AV_1-ezgif.com-video-to-webp-converter.webp?raw=true'
                })
            });
            return res.status(200).json(richData);
        }

        // Fallback — sendPhoto с HTML подписью
        const caption =
            `<b>НОВЫЙ ЗАКАЗ #${orderId}</b>\n\n` +
            `<b>Локация:</b> ${location || '—'}\n` +
            `<b>Позиция:</b> ${product || '—'}\n` +
            `<b>Сумма:</b> ${price || '—'}\n` +
            `<b>Оплата:</b> ${payMethod || '—'}\n` +
            (comment ? `<b>Комментарий:</b> ${comment}\n` : '') +
            `\n<b>Реквизиты для оплаты:</b>\n` +
            `<code>${requisites || '—'}</code>`;

        const photoRes = await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendPhoto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: chatId,
                photo: 'https://github.com/HuntersNetPlus/PvZ/blob/main/AV_1-ezgif.com-video-to-webp-converter.webp?raw=true',
                caption,
                parse_mode: 'HTML',
                reply_markup
            })
        });

        return res.status(200).json(await photoRes.json());

    } catch (err) {
        console.error('Send error:', err);
        return res.status(500).json({ ok: false, error: err.message });
    }
}
