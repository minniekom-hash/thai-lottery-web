// CSRF Token Helper
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Format numbers with comma
function formatCurrency(amount) {
    return Number(amount).toLocaleString('th-TH') + ' บาท';
}

// Single Ticket Checking
async function checkSingleTicket() {
    const ticketInput = document.getElementById('ticketInput');
    const drawDateSelect = document.getElementById('drawDateSelect');
    const resultContainer = document.getElementById('checkResultContainer');
    const btnCheck = document.getElementById('btnCheck');
    
    if (!ticketInput) return;
    
    const number = ticketInput.value.trim();
    const date = drawDateSelect ? drawDateSelect.value : '';
    
    if (number.length !== 6 || !/^\d{6}$/.test(number)) {
        alert('กรุณากรอกเลขสลากให้ครบ 6 หลัก (เฉพาะตัวเลขเท่านั้น)');
        ticketInput.focus();
        return;
    }
    
    // UI Loading state
    const originalBtnHtml = btnCheck.innerHTML;
    btnCheck.disabled = true;
    btnCheck.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>กำลังตรวจ...</span>';
    resultContainer.classList.add('hidden');
    resultContainer.innerHTML = '';
    
    try {
        const response = await fetch('/api/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken()
            },
            body: JSON.stringify({
                date: date,
                numbers: [number]
            })
        });
        
        const data = await response.json();
        
        if (!data.status) {
            resultContainer.innerHTML = `
                <div class="p-5 bg-rose-50/80 border border-rose-200/80 rounded-2xl text-rose-800 text-sm flex items-center gap-3">
                    <i class="fa-solid fa-circle-exclamation text-rose-500 text-lg"></i>
                    <span>${data.message || 'เกิดข้อผิดพลาดในการตรวจสอบ'}</span>
                </div>
            `;
            resultContainer.classList.remove('hidden');
            return;
        }
        
        const result = data.results[0];
        
        if (result.is_winner) {
            // Trigger Confetti!
            if (typeof confetti === 'function') {
                confetti({
                    particleCount: 160,
                    spread: 100,
                    origin: { y: 0.6 }
                });
            }
            
            let prizesHtml = result.prizes.map(p => `
                <div class="flex items-center justify-between py-2.5 border-b border-zinc-800/80 last:border-b-0 text-sm">
                    <div class="flex items-center gap-2.5">
                        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span class="font-semibold text-zinc-200">${p.name}</span>
                        <span class="text-xs text-zinc-500">(${p.detail})</span>
                    </div>
                    <span class="font-bold font-mono text-emerald-400 text-base">+${formatCurrency(p.reward)}</span>
                </div>
            `).join('');
            
            resultContainer.innerHTML = `
                <div class="bg-[#121215] border-2 border-emerald-500 rounded-3xl p-6 sm:p-8 shadow-2xl shadow-emerald-500/10 relative overflow-hidden">
                    <div class="text-center pb-5 border-b border-zinc-800">
                        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 text-xs font-semibold mb-3">
                            <i class="fa-solid fa-sparkles text-emerald-400"></i> ถูกรางวัลสลากกินแบ่งรัฐบาล
                        </div>
                        
                        <!-- โลโก้สำหรับคนที่ตรวจแล้วถูกรางวัล -->
                        <div class="flex justify-center mb-3">
                            <div class="relative inline-block">
                                <img src="/static/images/winner_shocked.jpg" alt="โลโก้คนถูกรางวัล" class="w-32 h-32 sm:w-40 sm:h-40 rounded-full object-cover border-4 border-emerald-500 shadow-xl shadow-emerald-500/20 transform hover:scale-105 transition-transform duration-300">
                                <span class="absolute -bottom-1 -right-1 bg-emerald-500 text-zinc-950 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shadow-md border-2 border-[#121215]">
                                    <i class="fa-solid fa-bolt"></i>
                                </span>
                            </div>
                        </div>

                        <!-- ข้อความแจ้งเตือนคนถูกรางวัลตามที่ระบุ เป็นตัวหนังสือสีเขียว -->
                        <h2 class="text-2xl sm:text-4xl font-extrabold text-emerald-400 tracking-tight font-heading my-2">
                            มึง!!! ถูกรางวัลได้ยังไงวะอีห่า
                        </h2>
                        
                        <p class="text-zinc-400 text-xs sm:text-sm mt-1">
                            สลากหมายเลข <span class="font-mono font-bold text-white text-lg sm:text-xl tracking-widest px-2.5 py-0.5 bg-zinc-900 border border-zinc-700 rounded-lg">${result.number}</span>
                        </p>
                    </div>

                    <div class="py-5 flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-zinc-800">
                        <div>
                            <span class="text-xs text-zinc-500 block">เงินรางวัลรวมที่คุณได้รับ</span>
                            <span class="text-3xl sm:text-4xl font-black font-heading text-emerald-400 tracking-tight">
                                ${formatCurrency(result.total_reward)}
                            </span>
                        </div>
                        <div class="text-right sm:text-right">
                            <span class="text-xs text-zinc-500 block">งวดประจำวันที่</span>
                            <span class="text-sm font-semibold text-zinc-300">${data.draw_date_thai}</span>
                        </div>
                    </div>

                    <div class="mt-5">
                        <h4 class="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">รายการรางวัลที่ถูก:</h4>
                        <div class="bg-zinc-900/90 rounded-2xl p-4 border border-zinc-800">
                            ${prizesHtml}
                        </div>
                    </div>
                </div>
            `;
        } else {
            resultContainer.innerHTML = `
                <div class="bg-[#121215] border-2 border-rose-500 rounded-3xl p-6 sm:p-8 text-center shadow-2xl shadow-rose-500/10 relative overflow-hidden">
                    <!-- โลโก้สำหรับคนไม่ถูกรางวัล -->
                    <div class="flex justify-center mb-3">
                        <div class="relative inline-block">
                            <img src="/static/images/loser_mocking.jpg" alt="โลโก้คนไม่ถูกรางวัล" class="w-32 h-32 sm:w-40 sm:h-40 rounded-full object-cover border-4 border-rose-500 shadow-xl shadow-rose-500/20 transform hover:scale-105 transition-transform duration-300">
                            <span class="absolute -bottom-1 -right-1 bg-rose-500 text-white w-8 h-8 rounded-full flex items-center justify-center text-xs shadow-md border-2 border-[#121215]">
                                <i class="fa-solid fa-face-laugh-squint"></i>
                            </span>
                        </div>
                    </div>

                    <!-- ข้อความแจ้งเตือนคนไม่ถูกรางวัลตามที่ระบุ เป็นตัวหนังสือสีแดง -->
                    <h2 class="text-2xl sm:text-4xl font-extrabold text-rose-500 tracking-tight font-heading my-2">
                        ว้าย!!!ถูกหวยแดกสมน้ำหน้าอีคนบาป
                    </h2>

                    <p class="text-zinc-400 text-xs sm:text-sm mt-2">
                        สลากหมายเลข <span class="font-mono font-bold text-white text-lg sm:text-xl tracking-widest px-2.5 py-0.5 bg-zinc-900 border border-zinc-700 rounded-lg">${result.number}</span> ไม่ถูกรางวัลใดๆ ในงวดนี้
                    </p>
                    <p class="text-[11px] text-zinc-500 mt-2">
                        งวดประจำวันที่ ${data.draw_date_thai} (ข้อมูลยืนยันจากสำนักงานสลากกินแบ่งรัฐบาล GLO)
                    </p>
                </div>
            `;
        }
        
        resultContainer.classList.remove('hidden');
        resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
    } catch (err) {
        resultContainer.innerHTML = `
            <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 text-sm">
                เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์ กรุณาลองใหม่อีกครั้ง
            </div>
        `;
        resultContainer.classList.remove('hidden');
    } finally {
        btnCheck.disabled = false;
        btnCheck.innerHTML = originalBtnHtml;
    }
}

// Bulk Tickets Checking
async function checkBulkTickets() {
    const bulkInput = document.getElementById('bulkNumbersInput');
    const bulkDate = document.getElementById('bulkDrawDate');
    const resultSection = document.getElementById('bulkResultSection');
    const btnSubmit = document.getElementById('btnBulkSubmit');
    
    if (!bulkInput) return;
    
    const rawText = bulkInput.value;
    const matches = rawText.match(/\b\d{6}\b/g) || [];
    
    if (matches.length === 0) {
        alert('กรุณากรอกหมายเลขสลาก 6 หลักอย่างน้อย 1 หมายเลข');
        bulkInput.focus();
        return;
    }
    
    const numbers = matches.slice(0, 50);
    const date = bulkDate ? bulkDate.value : '';
    
    const originalBtn = btnSubmit.innerHTML;
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>กำลังตรวจผลรางวัล...</span>';
    resultSection.classList.add('hidden');
    resultSection.innerHTML = '';
    
    try {
        const response = await fetch('/api/check', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken()
            },
            body: JSON.stringify({
                date: date,
                numbers: numbers
            })
        });
        
        const data = await response.json();
        
        if (!data.status) {
            resultSection.innerHTML = `
                <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 text-sm">
                    ${data.message || 'เกิดข้อผิดพลาด'}
                </div>
            `;
            resultSection.classList.remove('hidden');
            return;
        }
        
        let winningBannerHtml = '';
        if (data.total_winning_tickets > 0) {
            if (typeof confetti === 'function') {
                confetti({
                    particleCount: 180,
                    spread: 100,
                    origin: { y: 0.6 }
                });
            }
                winningBannerHtml = `
                <div class="mb-6 p-6 bg-[#121215] border-2 border-emerald-500 rounded-2xl text-center shadow-xl shadow-emerald-500/10">
                    <!-- โลโก้สำหรับคนที่ตรวจแล้วถูกรางวัล -->
                    <div class="flex justify-center mb-3">
                        <img src="/static/images/winner_shocked.jpg" alt="โลโก้คนถูกรางวัล" class="w-24 h-24 sm:w-28 sm:h-28 rounded-full object-cover border-4 border-emerald-500 shadow-md">
                    </div>
                    <span class="inline-block text-xs font-semibold px-2.5 py-1 bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 rounded-full mb-2">ยินดีด้วย</span>
                    <h3 class="text-2xl sm:text-3xl font-extrabold text-emerald-400 font-heading">
                        มึง!!! ถูกรางวัลได้ยังไงวะอีห่า
                    </h3>
                    <p class="text-xs text-emerald-300/80 mt-1">พบสลากที่ถูกรางวัลทั้งหมด ${data.total_winning_tickets} ใบ รวมเป็นเงิน ${formatCurrency(data.total_reward_sum)}</p>
                </div>
            `;
        } else {
            winningBannerHtml = `
                <div class="mb-6 p-6 bg-[#121215] border-2 border-rose-500 rounded-2xl text-center shadow-xl shadow-rose-500/10">
                    <!-- โลโก้สำหรับคนไม่ถูกรางวัล -->
                    <div class="flex justify-center mb-3">
                        <img src="/static/images/loser_mocking.jpg" alt="โลโก้คนไม่ถูกรางวัล" class="w-24 h-24 sm:w-28 sm:h-28 rounded-full object-cover border-4 border-rose-500 shadow-md">
                    </div>
                    <span class="inline-block text-xs font-semibold px-2.5 py-1 bg-rose-950/80 text-rose-400 border border-rose-800/80 rounded-full mb-2">เสียใจด้วย</span>
                    <h3 class="text-2xl sm:text-3xl font-extrabold text-rose-500 font-heading">
                        ว้าย!!!ถูกหวยแดกสมน้ำหน้าอีคนบาป
                    </h3>
                    <p class="text-xs text-rose-300/80 mt-1">สลากที่คุณตรวจทั้งหมด ${data.total_checked} ใบ ไม่มีใบไหนถูกรางวัลเลย</p>
                </div>
            `;
        }
        
        let rowsHtml = data.results.map((r, idx) => {
            if (r.is_winner) {
                const prizeList = r.prizes.map(p => `<span class="bg-emerald-950/70 text-emerald-300 border border-emerald-800/80 text-[11px] px-2 py-0.5 rounded-md font-semibold">${p.name} (+${formatCurrency(p.reward)})</span>`).join(' ');
                return `
                    <tr class="bg-emerald-950/20 hover:bg-emerald-950/40 transition">
                        <td class="p-4 text-center font-mono text-zinc-500 text-xs">${idx + 1}</td>
                        <td class="p-4 font-mono font-bold text-base text-white tracking-wider">${r.number}</td>
                        <td class="p-4">
                            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 text-xs font-bold">
                                <i class="fa-solid fa-circle-check text-emerald-400"></i> ถูกรางวัล
                            </span>
                        </td>
                        <td class="p-4">${prizeList}</td>
                        <td class="p-4 text-right font-bold font-mono text-emerald-400 text-base">${formatCurrency(r.total_reward)}</td>
                    </tr>
                `;
            } else {
                return `
                    <tr class="hover:bg-zinc-800/40 transition">
                        <td class="p-4 text-center font-mono text-zinc-500 text-xs">${idx + 1}</td>
                        <td class="p-4 font-mono text-zinc-300 tracking-wider">${r.number}</td>
                        <td class="p-4">
                            <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700/60 text-xs">
                                <i class="fa-solid fa-xmark text-zinc-500"></i> ไม่ถูกรางวัล
                            </span>
                        </td>
                        <td class="p-4 text-xs text-zinc-500">-</td>
                        <td class="p-4 text-right text-xs text-zinc-500">0 บาท</td>
                    </tr>
                `;
            }
        }).join('');
        
        resultSection.innerHTML = `
            <div class="bg-[#121215] rounded-3xl p-6 sm:p-8 shadow-xl border border-zinc-800">
                ${winningBannerHtml}
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 mb-6 border-b border-zinc-800 gap-4">
                    <div>
                        <h2 class="text-xl font-bold font-heading text-white">สรุปผลการตรวจรางวัล</h2>
                        <p class="text-xs text-zinc-400">งวดประจำวันที่ <strong class="text-zinc-200">${data.draw_date_thai}</strong></p>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="bg-zinc-900 px-3.5 py-2 rounded-xl border border-zinc-800 text-center">
                            <span class="text-[10px] text-zinc-500 font-medium block">ตรวจทั้งหมด</span>
                            <span class="text-base font-bold font-mono text-white">${data.total_checked}</span>
                        </div>
                        <div class="bg-emerald-950/50 px-3.5 py-2 rounded-xl border border-emerald-800/60 text-center">
                            <span class="text-[10px] text-emerald-400 font-medium block">ถูกรางวัล</span>
                            <span class="text-base font-bold font-mono text-emerald-400">${data.total_winning_tickets}</span>
                        </div>
                        <div class="bg-zinc-900 border border-zinc-800 text-white px-4 py-2 rounded-xl text-center">
                            <span class="text-[10px] text-zinc-400 font-medium block">ยอดเงินรางวัลรวม</span>
                            <span class="text-base font-bold font-mono text-emerald-400">${formatCurrency(data.total_reward_sum)}</span>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto rounded-2xl border border-zinc-800">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-zinc-900 text-zinc-400 text-xs border-b border-zinc-800">
                            <tr>
                                <th class="p-3.5 text-center w-12 font-medium">#</th>
                                <th class="p-3.5 font-medium">หมายเลขสลาก</th>
                                <th class="p-3.5 font-medium">สถานะ</th>
                                <th class="p-3.5 font-medium">รางวัล</th>
                                <th class="p-3.5 text-right font-medium">เงินรางวัล</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-zinc-800/80">
                            ${rowsHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth' });
        
    } catch (err) {
        resultSection.innerHTML = `
            <div class="p-4 bg-rose-50 border border-rose-200 rounded-2xl text-rose-800 text-sm">
                เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์
            </div>
        `;
        resultSection.classList.remove('hidden');
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = originalBtn;
    }
}

// Draw Date Dropdown on change (view draw)
document.addEventListener('DOMContentLoaded', () => {
    const drawDateSelect = document.getElementById('drawDateSelect');
    if (drawDateSelect) {
        drawDateSelect.addEventListener('change', (e) => {
            const date = e.target.value;
            if (date) {
                window.location.href = `/draw/${date}`;
            }
        });
    }
});
