/**
 * 협력기업 방문 일정 수립 - 메인 앱 로직
 * 카카오 지도 API 연동 + 경유지 관리 + 경로 계산
 */

(function () {
    'use strict';

    // ===== State =====
    const state = {
        apiKey: localStorage.getItem('kakao_js_key') || 'd83678527e52f4d753df486ac01f7d0c',
        apiSecret: localStorage.getItem('kakao_rest_key') || '007cb32ee7d003fec1bd6fc308b7ece7',
        departureTime: '09:00',
        memos: {}, // { id: { title, content } }
        lastSegments: [], // Store results for memo cards
        mapLoaded: false,
        map: null,
        markers: [],
        polylines: [],
        departure: null,   // { name, address, lat, lng }
        arrival: null,
        waypoints: [],      // [{ id, name, address, lat, lng }]
        waypointCounter: 0,
        searchTimeout: null
    };

    // ===== DOM References =====
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const els = {
        apiKeyModal: $('#apiKeyModal'),
        apiKeyInput: $('#apiKeyInput'),
        apiSecretInput: $('#apiSecretInput'),
        saveApiKeyBtn: $('#saveApiKeyBtn'),
        skipApiKeyBtn: $('#skipApiKeyBtn'),
        apiKeySettingBtn: $('#apiKeySettingBtn'),
        departureInput: $('#departureInput'),
        departureDropdown: $('#departureDropdown'),
        departureInfo: $('#departureInfo'),
        arrivalInput: $('#arrivalInput'),
        arrivalDropdown: $('#arrivalDropdown'),
        arrivalInfo: $('#arrivalInfo'),
        waypointsContainer: $('#waypointsContainer'),
        addWaypointBtn: $('#addWaypointBtn'),
        calcRouteBtn: $('#calcRouteBtn'),
        optimizeBtn: $('#optimizeBtn'),
        departureTimeInput: $('#departureTime'),
        resetBtn: $('#resetBtn'),
        resultPanel: $('#resultPanel'),
        resultSummary: $('#resultSummary'),
        resultSegments: $('#resultSegments'),
        mapPlaceholder: $('#mapPlaceholder'),
        mapContainer: $('#mapContainer'),
        memosContainer: $('#memosContainer'),
        toast: $('#toast')
    };

    // ===== Init =====
    function init() {
        setupEventListeners();
        if (state.apiKey) {
            hideModal();
            loadKakaoMapScript();
        }
    }

    // ===== Event Listeners =====
    function setupEventListeners() {
        els.saveApiKeyBtn.addEventListener('click', saveApiKey);
        els.skipApiKeyBtn.addEventListener('click', () => {
            hideModal();
            showToast('🗺️ 데모 모드로 실행합니다. 경유지 추가/삭제를 테스트해보세요!');
        });
        els.apiKeySettingBtn.addEventListener('click', showModal);
        els.addWaypointBtn.addEventListener('click', addWaypoint);
        els.calcRouteBtn.addEventListener('click', calculateRoute);
        els.optimizeBtn.addEventListener('click', optimizeRoute);
        els.resetBtn.addEventListener('click', resetAll);

        // Departure search
        setupSearch(els.departureInput, els.departureDropdown, (place) => {
            state.departure = place;
            els.departureInput.value = place.name;
            els.departureInput.classList.add('has-value');
            els.departureInfo.textContent = place.address;
            els.departureInfo.classList.add('has-info');
            updateButtonStates();
            updateMap();
        });

        // Arrival search
        setupSearch(els.arrivalInput, els.arrivalDropdown, (place) => {
            state.arrival = place;
            els.arrivalInput.value = place.name;
            els.arrivalInput.classList.add('has-value');
            els.arrivalInfo.textContent = place.address;
            els.arrivalInfo.classList.add('has-info');
            updateButtonStates();
            updateMap();
        });

        // Close dropdowns on outside click
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-wrapper')) {
                $$('.search-dropdown').forEach(d => d.classList.remove('active'));
            }
        });
    }

    // ===== API Key =====
    function saveApiKey() {
        const key = els.apiKeyInput.value.trim();
        const secret = els.apiSecretInput.value.trim();
        if (key && secret) {
            state.apiKey = key;
            state.apiSecret = secret;
            localStorage.setItem('kakao_js_key', key);
            localStorage.setItem('kakao_rest_key', secret);
            hideModal();
            loadKakaoMapScript();
            showToast('✅ API Key 및 Secret이 저장되었습니다!');
        } else {
            showToast('⚠️ JavaScript 키와 REST API 키를 모두 입력해주세요.');
        }
    }

    function showModal() {
        els.apiKeyModal.classList.remove('hidden');
        els.apiKeyInput.value = state.apiKey;
        els.apiSecretInput.value = state.apiSecret;
        setTimeout(() => els.apiKeyInput.focus(), 300);
    }

    function hideModal() {
        els.apiKeyModal.classList.add('hidden');
    }

    // ===== Kakao Map =====
    function loadKakaoMapScript() {
        if (state.mapLoaded || !state.apiKey) return;
        const script = document.createElement('script');
        // Kakao Maps API with autoload=false
        script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${state.apiKey}&autoload=false&libraries=services`;
        script.onload = () => {
            kakao.maps.load(() => {
                state.mapLoaded = true;
                initMap();
            });
        };
        script.onerror = () => {
            showToast('❌ 지도 로드에 실패했습니다. JavaScript 키와 [플랫폼 > Web] 도메인 등록을 확인해주세요.');
        };
        document.head.appendChild(script);
    }

    function initMap() {
        if (!window.kakao || !window.kakao.maps) return;
        els.mapPlaceholder.style.display = 'none';
        const mapOption = {
            center: new kakao.maps.LatLng(37.3595704, 127.105399),
            level: 5 // Kakao zoom level (smaller = closer)
        };
        state.map = new kakao.maps.Map(els.mapContainer, mapOption);

        // Add zoom control
        const zoomControl = new kakao.maps.ZoomControl();
        state.map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);
    }

    function updateMap() {
        if (!state.map) return;
        clearMapObjects();
        const points = getAllPoints();
        if (points.length === 0) return;

        const bounds = new kakao.maps.LatLngBounds();

        points.forEach((p, i) => {
            const pos = new kakao.maps.LatLng(p.lat, p.lng);
            bounds.extend(pos);
            const isFirst = i === 0;
            const isLast = i === points.length - 1;

            // Custom marker using CustomOverlay
            const content = `
                <div style="
                    background:${isFirst ? '#2ecc71' : isLast ? '#e74c3c' : '#3498db'};
                    color:#fff; font-weight:700; font-size:12px;
                    width:28px; height:28px; border-radius:50%;
                    display:flex; align-items:center; justify-content:center;
                    box-shadow:0 2px 8px rgba(0,0,0,0.3);
                    border:2px solid #fff;">${i + 1}</div>`;

            const overlay = new kakao.maps.CustomOverlay({
                position: pos,
                content: content,
                map: state.map,
                yAnchor: 0.5
            });
            state.markers.push(overlay);
        });

        // Draw polylines between consecutive points
        if (points.length >= 2) {
            const path = points.map(p => new kakao.maps.LatLng(p.lat, p.lng));
            const polyline = new kakao.maps.Polyline({
                map: state.map,
                path: path,
                strokeColor: '#2ecc71',
                strokeWeight: 3,
                strokeOpacity: 0.8,
                strokeStyle: 'shortdash'
            });
            state.polylines.push(polyline);
        }

        state.map.setBounds(bounds);
    }

    function clearMapObjects() {
        state.markers.forEach(m => m.setMap(null));
        state.polylines.forEach(p => p.setMap(null));
        state.markers = [];
        state.polylines = [];
    }

    function getAllPoints() {
        const points = [];
        if (state.departure) points.push(state.departure);
        state.waypoints.forEach(wp => {
            if (wp.lat && wp.lng) points.push(wp);
        });
        if (state.arrival) points.push(state.arrival);
        return points;
    }

    // ===== Search =====
    function setupSearch(input, dropdown, onSelect) {
        let debounceTimer;
        input.addEventListener('input', () => {
            const query = input.value.trim();
            if (query.length < 2) {
                dropdown.classList.remove('active');
                return;
            }
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => searchPlaces(query, dropdown, onSelect), 300);
        });

        input.addEventListener('focus', () => {
            if (dropdown.children.length > 0) {
                dropdown.classList.add('active');
            }
        });
    }

    async function searchPlaces(query, dropdown, onSelect) {
        try {
            const url = `http://127.0.0.1:5000/api/search?query=${encodeURIComponent(query)}`;
            console.log(`DEBUG: Sending search request to proxy: ${url}`);
            
            const response = await fetch(url, {
                headers: {
                    'X-NCP-APIGW-API-KEY': state.apiSecret
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error('DEBUG: Proxy Error:', errorData);
                throw new Error(`Proxy status: ${response.status}`);
            }

            const data = await response.json();
            console.log(`DEBUG: Search successful, found ${data.documents ? data.documents.length : 0} items`);
            
            if (data.documents && data.documents.length > 0) {
                dropdown.innerHTML = '';
                data.documents.forEach(item => {
                    const div = createDropdownItem({
                        name: item.place_name,
                        address: item.road_address_name || item.address_name,
                        category: item.category_group_name,
                        lat: parseFloat(item.y),
                        lng: parseFloat(item.x)
                    }, onSelect, dropdown);
                    dropdown.appendChild(div);
                });
                dropdown.classList.add('active');
                return;
            }
        } catch (e) {
            console.error("DEBUG: Search failed entirely:", e);
            if (e.message.includes('Failed to fetch')) {
                showToast('❌ 백엔드 서버(Flask)가 꺼져있는 것 같습니다! 터미널을 확인해주세요.');
            }
        }

        // Fallback to Demo Results
        showDemoResults(query, dropdown, onSelect);
    }

    // Demo results when API is not available
    function showDemoResults(query, dropdown, onSelect) {
        const demoPlaces = [
            { name: '풀무원 본사', address: '서울특별시 강남구 테헤란로 340', category: '기업 본사', lat: 37.5085, lng: 127.0622 },
            { name: '풀무원 음성공장', address: '충청북도 음성군 대소면 풀무원로 1', category: '제조공장', lat: 36.9381, lng: 127.5867 },
            { name: '풀무원 춘천공장', address: '강원도 춘천시 동면 풀무원길 50', category: '제조공장', lat: 37.8813, lng: 127.7689 },
            { name: '풀무원 익산공장', address: '전라북도 익산시 왕궁면 풀무원로 100', category: '제조공장', lat: 35.9584, lng: 127.0012 },
            { name: '풀무원 연구소', address: '경기도 용인시 처인구 남사읍 봉무로 200', category: '연구개발', lat: 37.1342, lng: 127.1234 },
            { name: '서울역', address: '서울특별시 용산구 한강대로 405', category: '교통', lat: 37.5547, lng: 126.9707 },
            { name: '수원역', address: '경기도 수원시 팔달구 덕영대로 924', category: '교통', lat: 37.2660, lng: 127.0001 },
            { name: '인천국제공항', address: '인천광역시 중구 공항로 272', category: '공항', lat: 37.4602, lng: 126.4407 },
        ];

        const filtered = demoPlaces.filter(p =>
            p.name.includes(query) || p.address.includes(query)
        );

        dropdown.innerHTML = '';
        if (filtered.length === 0) {
            // Show a "no results" message with demo suggestion
            const noResult = document.createElement('div');
            noResult.className = 'dropdown-item';
            noResult.innerHTML = `
                <div class="dropdown-item-name" style="color:var(--text-muted)">검색 결과 없음</div>
                <div class="dropdown-item-address">API Key를 설정하면 실제 장소를 검색할 수 있습니다.</div>
            `;
            dropdown.appendChild(noResult);
            // Also still show all demo places below
            demoPlaces.slice(0, 5).forEach(place => {
                dropdown.appendChild(createDropdownItem(place, onSelect, dropdown));
            });
        } else {
            filtered.forEach(place => {
                dropdown.appendChild(createDropdownItem(place, onSelect, dropdown));
            });
        }
        dropdown.classList.add('active');
    }

    function createDropdownItem(place, onSelect, dropdown) {
        const div = document.createElement('div');
        div.className = 'dropdown-item';
        div.innerHTML = `
            <div class="dropdown-item-name">${place.name}</div>
            <div class="dropdown-item-address">${place.address}</div>
            ${place.category ? `<div class="dropdown-item-category">${place.category}</div>` : ''}
        `;
        div.addEventListener('click', () => {
            onSelect(place);
            dropdown.classList.remove('active');
        });
        return div;
    }

    // ===== Waypoints =====
    function addWaypoint() {
        state.waypointCounter++;
        const id = 'wp_' + state.waypointCounter;
        const wpData = { id, name: '', address: '', lat: null, lng: null };
        state.waypoints.push(wpData);

        const wpEl = document.createElement('div');
        wpEl.className = 'waypoint-item';
        wpEl.dataset.waypointId = id;
        wpEl.innerHTML = `
            <div class="route-marker">
                <div class="marker-line marker-line-top"></div>
                <div class="marker-dot waypoint-dot"></div>
                <div class="marker-line"></div>
            </div>
            <div class="waypoint-input-group">
                <div class="waypoint-header">
                    <label>경유지 ${state.waypointCounter}</label>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <div class="time-input-wrapper">
                            <span>체류:</span>
                            <input type="number" class="stay-duration-input" value="30" min="0" step="10">
                            <span>분</span>
                        </div>
                        <button class="btn-remove-waypoint" data-id="${id}" title="삭제">✕</button>
                    </div>
                </div>
                <div class="search-wrapper">
                    <input type="text" class="location-input" placeholder="경유 장소를 검색하세요" autocomplete="off">
                    <div class="search-dropdown"></div>
                </div>
                <div class="location-info"></div>
            </div>
        `;

        els.waypointsContainer.appendChild(wpEl);

        // Setup search for this waypoint
        const wpInput = wpEl.querySelector('.location-input');
        const wpDropdown = wpEl.querySelector('.search-dropdown');
        const wpInfo = wpEl.querySelector('.location-info');

        setupSearch(wpInput, wpDropdown, (place) => {
            wpData.name = place.name;
            wpData.address = place.address;
            wpData.lat = place.lat;
            wpData.lng = place.lng;
            wpInput.value = place.name;
            wpInput.classList.add('has-value');
            wpInfo.textContent = place.address;
            wpInfo.classList.add('has-info');
            updateButtonStates();
            updateMap();
        });

        // Remove button
        wpEl.querySelector('.btn-remove-waypoint').addEventListener('click', () => {
            removeWaypoint(id, wpEl);
        });

        updateButtonStates();
        wpInput.focus();
        showToast(`📍 경유지 ${state.waypointCounter}이(가) 추가되었습니다.`);
    }

    function removeWaypoint(id, el) {
        state.waypoints = state.waypoints.filter(wp => wp.id !== id);
        el.style.animation = 'slideIn 0.2s ease reverse';
        setTimeout(() => {
            el.remove();
            renumberWaypoints();
            updateButtonStates();
            updateMap();
        }, 200);
    }

    function renumberWaypoints() {
        const items = els.waypointsContainer.querySelectorAll('.waypoint-item');
        items.forEach((item, i) => {
            const label = item.querySelector('.waypoint-header label');
            if (label) label.textContent = `경유지 ${i + 1}`;
        });
    }

    // ===== Button States =====
    function updateButtonStates() {
        const hasDeparture = state.departure !== null;
        const hasArrival = state.arrival !== null;
        els.calcRouteBtn.disabled = !(hasDeparture && hasArrival);
        els.optimizeBtn.disabled = !(hasDeparture && hasArrival && state.waypoints.length >= 2);
        updateMemos();
    }

    // ===== Memos =====
    function updateMemos() {
        const container = els.memosContainer;
        const allPoints = getAllPoints();
        
        if (allPoints.length === 0) {
            container.innerHTML = `
                <div class="memo-empty">
                    <div class="memo-empty-icon">✍️</div>
                    <p>장소를 선택하시면<br>메모를 작성할 수 있습니다.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        allPoints.forEach((point, i) => {
            const id = point.id || (i === 0 ? 'departure' : 'arrival');
            if (!state.memos[id]) {
                state.memos[id] = { title: '', content: '' };
            }
            
            const card = document.createElement('div');
            card.className = 'memo-card';
            
            // Find timing/road info for this point if available
            let arrivalInfo = '';
            let roadBadges = '';
            if (state.lastSegments.length > 0) {
                if (i === 0) {
                    arrivalInfo = `<span class="memo-arrival" style="color:var(--accent-green)">출발: ${els.departureTimeInput.value}</span>`;
                } else {
                    const seg = state.lastSegments[i - 1];
                    if (seg) {
                        arrivalInfo = `<span class="memo-arrival" style="color:var(--accent-blue)">도착: ${seg.arrTime}</span>`;
                        roadBadges = `<div class="memo-road-sequence">
                            ${(seg.majorRoads || []).map((r, ri) => `
                                <span class="road-item ${r.type === 'express' ? 'express' : ''}">${r.name}</span>
                                ${ri < seg.majorRoads.length - 1 ? '<span class="road-sep">>></span>' : ''}
                            `).join('')}
                        </div>`;
                    }
                }
            }

            card.innerHTML = `
                <div class="memo-card-header">
                    <div class="memo-card-icon" style="background:${i === 0 ? 'var(--accent-green)' : (i === allPoints.length - 1 ? 'var(--accent-red)' : 'var(--accent-blue)')}"></div>
                    <div class="memo-card-title-group">
                        <div class="memo-card-title">${point.name || (i === 0 ? '출발지' : (i === allPoints.length - 1 ? '도착지' : '경유지 ' + i))}</div>
                        ${arrivalInfo}
                    </div>
                </div>
                ${roadBadges}
                <div class="memo-field">
                    <label>메모 제목</label>
                    <input type="text" class="memo-input" placeholder="업무 제목을 입력하세요" value="${state.memos[id].title}">
                </div>
                <div class="memo-field">
                    <label>상세 내용</label>
                    <textarea class="memo-textarea" placeholder="상세 내용을 입력하세요">${state.memos[id].content}</textarea>
                </div>
            `;
            
            // Event Listeners for saving
            card.querySelector('.memo-input').addEventListener('input', (e) => {
                state.memos[id].title = e.target.value;
            });
            card.querySelector('.memo-textarea').addEventListener('input', (e) => {
                state.memos[id].content = e.target.value;
            });
            
            container.appendChild(card);
        });
    }

    // ===== Route Calculation =====
    async function calculateRoute() {
        const points = getAllPoints();
        if (points.length < 2) {
            showToast('⚠️ 출발지와 도착지를 모두 입력해주세요.');
            return;
        }

        showToast('🔄 카카오 길찾기 API를 호출하고 있습니다...');

        try {
            const start = `${points[0].lng},${points[0].lat}`;
            const goal = `${points[points.length - 1].lng},${points[points.length - 1].lat}`;
            let waypointsParam = '';

            if (points.length > 2) {
                const wps = points.slice(1, points.length - 1);
                waypointsParam = wps.map(p => `${p.lng},${p.lat}`).join('|');
            }

            let url = `http://127.0.0.1:5000/api/directions?start=${start}&goal=${goal}`;
            if (waypointsParam) {
                url += `&waypoints=${waypointsParam}`;
            }

            const response = await fetch(url, {
                headers: {
                    'X-NCP-APIGW-API-KEY': state.apiSecret
                }
            });

            const data = await response.json();

            if (!response.ok || (data.routes && data.routes[0].result_code === 104)) {
                console.error("API Error:", data);
                throw new Error(data.msg || '카카오 API 호출 실패');
            }

            const route = data.routes[0];
            const totalDistance = route.summary.distance / 1000; // m -> km
            const totalTime = Math.round(route.summary.duration / 60); // sec -> min

            // Extract path from all sections and roads
            const fullPath = [];
            route.sections.forEach(section => {
                section.roads.forEach(road => {
                    for (let i = 0; i < road.vertexes.length; i += 2) {
                        fullPath.push({
                            x: road.vertexes[i],
                            y: road.vertexes[i + 1]
                        });
                    }
                });
            });

            // Draw real polyline and map markers
            drawRealRouteOnMap(fullPath);

            // Generate segments breakdown from sections
            const startTimeStr = els.departureTimeInput.value;
            let [h, m] = startTimeStr.split(':').map(Number);
            let currentTime = h * 60 + m; // Total minutes from 00:00

            const waypointsEls = els.waypointsContainer.querySelectorAll('.waypoint-item');
            const stayDurations = Array.from(waypointsEls).map(el => 
                parseInt(el.querySelector('.stay-duration-input').value) || 0
            );

            const formatTime = (totalMin) => {
                const hh = Math.floor((totalMin % 1440) / 60);
                const mm = totalMin % 60;
                return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
            };

            const segments = route.sections.map((section, i) => {
                const depTime = formatTime(currentTime);
                const durMin = Math.round(section.duration / 60);
                const arrTime = formatTime(currentTime + durMin);
                
                // Extract Major Roads Sequence (Optimized)
                const roadSequence = [];
                section.roads.forEach(r => {
                    const name = r.name;
                    if (!name || name.trim() === '') return;
                    const processedName = name.includes('고속도로') ? name : '국도';
                    if (roadSequence.length === 0 || roadSequence[roadSequence.length - 1].name !== processedName) {
                        roadSequence.push({
                            name: processedName,
                            type: processedName === '국도' ? 'local' : 'express'
                        });
                    }
                });

                // Extract Key Nodes (IC, JC, TG)
                const keyNodes = section.guides
                    .filter(g => g.name && (g.name.includes('IC') || g.name.includes('JC') || g.name.includes('TG') || g.name.includes('톨게이트')))
                    .map(g => g.name);
                const uniqueNodes = [...new Set(keyNodes)].slice(0, 4); // Limit to top 4 key points

                const segment = {
                    from: points[i].name,
                    to: points[i+1].name,
                    distance: section.distance / 1000,
                    time: durMin,
                    depTime: depTime,
                    arrTime: arrTime,
                    majorRoads: roadSequence,
                    keyNodes: uniqueNodes
                };

                // Update currentTime for next segment (Arrival + Stay at destination of this segment)
                if (i < stayDurations.length) {
                    currentTime += durMin + stayDurations[i];
                } else {
                    currentTime += durMin;
                }
                
                return segment;
            });

            displayResults(segments, totalDistance, totalTime);
            state.lastSegments = segments;
            updateMemos();

        } catch (error) {
            showToast(`❌ 길찾기 오류: ${error.message} (가상 경로로 대체합니다)`);
            fallbackCalculateRoute(points);
        }
    }

    function fallbackCalculateRoute(points) {
        const segments = [];
        let totalDistance = 0;
        let totalTime = 0;

        for (let i = 0; i < points.length - 1; i++) {
            const from = points[i];
            const to = points[i + 1];
            const dist = haversineDistance(from.lat, from.lng, to.lat, to.lng);
            const time = Math.round(dist / 50 * 60);

            segments.push({
                from: from.name,
                to: to.name,
                distance: dist,
                time: time,
                majorRoads: [],
                keyNodes: []
            });
            totalDistance += dist;
            totalTime += time;
        }

        displayResults(segments, totalDistance, totalTime);
        updateMap();
    }

    function drawRealRouteOnMap(pathData) {
        clearMapObjects();
        const points = getAllPoints();
        const bounds = new kakao.maps.LatLngBounds();

        // Draw Markers
        points.forEach((p, i) => {
            const pos = new kakao.maps.LatLng(p.lat, p.lng);
            bounds.extend(pos);
            const isFirst = i === 0;
            const isLast = i === points.length - 1;

            const content = `
                <div style="
                    background:${isFirst ? '#2ecc71' : isLast ? '#e74c3c' : '#3498db'};
                    color:#fff; font-weight:700; font-size:12px;
                    width:28px; height:28px; border-radius:50%;
                    display:flex; align-items:center; justify-content:center;
                    box-shadow:0 2px 8px rgba(0,0,0,0.3);
                    border:2px solid #fff;">${i + 1}</div>`;

            const overlay = new kakao.maps.CustomOverlay({
                position: pos,
                content: content,
                map: state.map,
                yAnchor: 0.5
            });
            state.markers.push(overlay);
        });

        // Draw real polyline
        // Kakao pathData should be flattened or structured correctly.
        // Assuming pathData from Kakao Mobility Directions contains coordinates.
        const linePath = [];
        pathData.forEach(pos => {
            const latlng = new kakao.maps.LatLng(pos.y, pos.x);
            linePath.push(latlng);
            bounds.extend(latlng);
        });

        const polyline = new kakao.maps.Polyline({
            map: state.map,
            path: linePath,
            strokeColor: '#3498db',
            strokeWeight: 6,
            strokeOpacity: 0.8,
            strokeStyle: 'solid'
        });
        state.polylines.push(polyline);
        state.map.setBounds(bounds);
    }

    function haversineDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // km
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) ** 2;
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    function displayResults(segments, totalDistance, totalTime) {
        if (!els.resultPanel || !els.resultSegments) return;

        // Header Summary
        els.resultSummary.innerHTML = `
            <div class="summary-item">
                <span class="summary-label">총 거리</span>
                <span class="summary-value">${totalDistance.toFixed(1)}km</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">총 소요시간</span>
                <span class="summary-value">${Math.floor(totalTime / 60)}h ${totalTime % 60}m</span>
            </div>
            <div class="summary-item">
                <span class="summary-label">방문처</span>
                <span class="summary-value">${state.waypoints.filter(w => w.lat).length + 1}곳</span>
            </div>
        `;

        const allPoints = getAllPoints();
        const waypointsEls = els.waypointsContainer.querySelectorAll('.waypoint-item');
        const stayDurations = Array.from(waypointsEls).map(el => 
            parseInt(el.querySelector('.stay-duration-input').value) || 0
        );

        let tableHtml = `
            <table class="itinerary-table">
                <thead>
                    <tr>
                        <th style="width: 18%;">시 간</th>
                        <th style="width: 25%;">일 정</th>
                        <th style="width: 20%;">소요시간</th>
                        <th style="width: 37%;">비 고</th>
                    </tr>
                </thead>
                <tbody>
        `;

        segments.forEach((seg, i) => {
            // 1. Travel Row
            tableHtml += `
                <tr class="row-travel">
                    <td class="col-time">${seg.depTime} ~<br>${seg.arrTime}</td>
                    <td class="col-schedule">${seg.from} ~<br>${seg.to}</td>
                    <td class="col-duration">
                        <div class="dur-val">${seg.time} min</div>
                        <div class="dist-val">(약 ${seg.distance.toFixed(1)} km)</div>
                        <div class="road-info">${(seg.majorRoads || []).map(r => r.name).join(' >> ')}</div>
                    </td>
                    <td class="col-remarks">
                        ${(seg.keyNodes || []).map(n => `<span class="tag-node">${n}</span>`).join(' ')}
                    </td>
                </tr>
            `;

            // 2. Stay Row
            if (i < segments.length) {
                const point = allPoints[i + 1];
                const id = point.id || `${point.lat}-${point.lng}`;
                const stayMin = i < stayDurations.length ? stayDurations[i] : 0;
                
                const memo = state.memos[id] || { title: '', content: '' };
                const startTime = seg.arrTime;
                
                let [h, m] = startTime.split(':').map(Number);
                let endMin = h * 60 + m + stayMin;
                const endTime = `${String(Math.floor((endMin % 1440) / 60)).padStart(2, '0')}:${String(endMin % 60).padStart(2, '0')}`;

                tableHtml += `
                    <tr class="row-stay">
                        <td class="col-time">${startTime} ~<br>${endTime}</td>
                        <td class="col-schedule"><strong>${point.name}</strong></td>
                        <td class="col-duration">${stayMin} min</td>
                        <td class="col-remarks">
                            <div class="remark-addr">${point.address || ''}</div>
                            ${memo.title ? `<div class="remark-title">📌 ${memo.title}</div>` : ''}
                            ${memo.content ? `<div class="remark-content">${memo.content}</div>` : ''}
                        </td>
                    </tr>
                `;
            }
        });

        tableHtml += `
                </tbody>
            </table>
        `;

        els.resultSegments.innerHTML = tableHtml;
        els.resultPanel.classList.add('visible');
        showToast('✅ 주행 일정이 비즈니스 보고서 형태로 생성되었습니다!');
    }

    function formatTime(minutes) {
        if (minutes < 60) return `${minutes}분`;
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return m > 0 ? `${h}시간 ${m}분` : `${h}시간`;
    }

    // ===== Optimize Route =====
    function optimizeRoute() {
        const validWaypoints = state.waypoints.filter(wp => wp.lat && wp.lng);
        if (validWaypoints.length < 2) {
            showToast('⚠️ 최적화하려면 경유지가 2개 이상 필요합니다.');
            return;
        }

        showToast('🔄 경유지 순서를 최적화하고 있습니다...');

        // Simple nearest-neighbor optimization
        const optimized = nearestNeighborOptimize(state.departure, validWaypoints, state.arrival);

        // Reorder waypoints in state
        const reorderedIds = optimized.map(wp => wp.id);
        state.waypoints = reorderedIds.map(id => state.waypoints.find(wp => wp.id === id))
            .filter(Boolean)
            .concat(state.waypoints.filter(wp => !wp.lat || !wp.lng));

        // Reorder DOM elements
        const container = els.waypointsContainer;
        reorderedIds.forEach(id => {
            const el = container.querySelector(`[data-waypoint-id="${id}"]`);
            if (el) container.appendChild(el);
        });
        renumberWaypoints();

        // Recalculate
        setTimeout(() => calculateRoute(), 300);
        showToast('✅ 경유지 순서가 최적화되었습니다!');
    }

    function nearestNeighborOptimize(start, waypoints, end) {
        if (waypoints.length === 0) return [];

        let remaining = [...waypoints];
        let result = [];
        let current = start;

        // 1. Initial Nearest Neighbor
        while (remaining.length > 0) {
            let nearestIdx = 0;
            let nearestDist = Infinity;
            remaining.forEach((wp, i) => {
                const d = haversineDistance(current.lat, current.lng, wp.lat, wp.lng);
                if (d < nearestDist) {
                    nearestDist = d;
                    nearestIdx = i;
                }
            });
            current = remaining.splice(nearestIdx, 1)[0];
            result.push(current);
        }

        // 2. 2-opt Improvement (Local Search)
        // Only if we have enough waypoints to swap
        if (result.length >= 2) {
            result = twoOptImprove(start, result, end);
        }

        return result;
    }

    function twoOptImprove(start, waypoints, end) {
        let bestPath = [...waypoints];
        let improved = true;

        const getFullDistance = (path) => {
            let dist = 0;
            let p = [start, ...path, end];
            for (let i = 0; i < p.length - 1; i++) {
                dist += haversineDistance(p[i].lat, p[i].lng, p[i + 1].lat, p[i + 1].lng);
            }
            return dist;
        };

        let bestDist = getFullDistance(bestPath);

        // Limit iterations to prevent hanging
        let iterations = 0;
        while (improved && iterations < 50) {
            improved = false;
            iterations++;
            for (let i = 0; i < bestPath.length - 1; i++) {
                for (let j = i + 1; j < bestPath.length; j++) {
                    // Reverse the segment between i and j
                    const newPath = [...bestPath];
                    const segment = newPath.slice(i, j + 1).reverse();
                    newPath.splice(i, j - i + 1, ...segment);

                    const newDist = getFullDistance(newPath);
                    if (newDist < bestDist) {
                        bestDist = newDist;
                        bestPath = newPath;
                        improved = true;
                    }
                }
            }
        }
        return bestPath;
    }

    // ===== Reset =====
    function resetAll() {
        state.departure = null;
        state.arrival = null;
        state.waypoints = [];
        state.waypointCounter = 0;

        els.departureInput.value = '';
        els.departureInput.classList.remove('has-value');
        els.departureInfo.textContent = '';
        els.departureInfo.classList.remove('has-info');

        els.arrivalInput.value = '';
        els.arrivalInput.classList.remove('has-value');
        els.arrivalInfo.textContent = '';
        els.arrivalInfo.classList.remove('has-info');

        els.waypointsContainer.innerHTML = '';
        els.resultPanel.classList.remove('visible');

        updateButtonStates();
        clearMapObjects();

        if (state.map) {
            state.map.setCenter(new kakao.maps.LatLng(37.3595704, 127.105399));
            state.map.setLevel(5);
        }

        showToast('🔄 모든 입력이 초기화되었습니다.');
    }

    // ===== Toast =====
    let toastTimer;
    function showToast(msg) {
        clearTimeout(toastTimer);
        els.toast.textContent = msg;
        els.toast.classList.add('show');
        toastTimer = setTimeout(() => els.toast.classList.remove('show'), 3000);
    }

    // ===== Start =====
    document.addEventListener('DOMContentLoaded', init);
})();
