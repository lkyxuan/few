#!/usr/bin/env python3
"""
监控服务API接口
提供RESTful API供各个服务发送监控事件和查询监控数据
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.event_router import EventRouter
from core.config_manager import ConfigManager


class EventRequest(BaseModel):
    """事件请求模型"""
    service: str = Field(..., description="服务名称")
    event_type: str = Field(..., description="事件类型")
    level: str = Field(..., description="事件级别: info, warning, error, critical")
    message: str = Field(..., description="事件消息")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细信息")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="指标数据")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳")


class TestEventRequest(BaseModel):
    """测试事件请求模型"""
    service: str = Field(default="monitor", description="服务名称")
    message: str = Field(default="测试事件", description="测试消息")


def create_monitor_app(event_router: EventRouter, config_manager: ConfigManager) -> FastAPI:
    """
    创建监控服务FastAPI应用
    
    Args:
        event_router: 事件路由器
        config_manager: 配置管理器
        
    Returns:
        FastAPI应用实例
    """
    app = FastAPI(
        title="DataBao Monitor Service",
        description="DataBao集中监控服务API",
        version="1.0.0"
    )
    
    logger = logging.getLogger('monitor.api')
    
    # 健康检查端点
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {
            "service": "DataBao Monitor",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # 事件发送端点
    @app.post("/api/events")
    async def send_event(event: EventRequest):
        """
        接收监控事件
        
        接收来自各个服务的监控事件，根据配置规则路由到相应的webhook
        """
        try:
            logger.info(f"收到事件: {event.service}.{event.event_type} [{event.level}]")
            
            # 处理事件
            result = await event_router.process_event(event.dict())
            
            if result['success']:
                return {
                    "success": True,
                    "message": result['message'],
                    "routes_matched": result.get('routes_matched', 0),
                    "results": result.get('results', [])
                }
            else:
                logger.error(f"事件处理失败: {result.get('error')}")
                raise HTTPException(status_code=500, detail=result.get('error'))
                
        except Exception as e:
            logger.error(f"API事件处理异常: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 获取最近事件
    @app.get("/api/events")
    async def get_recent_events(
        limit: int = 50,
        service: str = None,
        level: str = None
    ):
        """
        获取最近的监控事件
        
        Args:
            limit: 返回事件数量限制（默认50）
            service: 过滤服务名
            level: 过滤事件级别
        """
        try:
            events = event_router.get_recent_events(
                limit=limit,
                service=service,
                level=level
            )
            
            return {
                "success": True,
                "events": events,
                "total": len(events)
            }
            
        except Exception as e:
            logger.error(f"获取事件列表失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 获取事件统计
    @app.get("/api/stats")
    async def get_event_stats():
        """获取事件统计信息"""
        try:
            stats = event_router.get_event_stats()
            return {
                "success": True,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 获取配置信息
    @app.get("/api/config")
    async def get_config():
        """获取监控配置信息"""
        try:
            config_summary = config_manager.get_config_summary()
            return {
                "success": True,
                "config": config_summary
            }
        except Exception as e:
            logger.error(f"获取配置信息失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 重新加载配置
    @app.post("/api/config/reload")
    async def reload_config():
        """重新加载配置"""
        try:
            await config_manager.reload_config()
            # 重新加载webhook路由器的配置
            await event_router.webhook_router.load_config()
            
            return {
                "success": True,
                "message": "配置重新加载成功",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 发送测试事件
    @app.post("/api/test-event")
    async def send_test_event(test_req: TestEventRequest):
        """发送测试事件"""
        try:
            result = await event_router.send_test_event(
                service=test_req.service,
                message=test_req.message
            )
            
            return {
                "success": True,
                "message": "测试事件已发送",
                "result": result
            }
        except Exception as e:
            logger.error(f"发送测试事件失败: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 简单的Web管理界面
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Web管理界面"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>DataBao Monitor Dashboard</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .stats { display: flex; gap: 20px; }
        .stat-box { padding: 10px; background: #e8f4f8; border-radius: 5px; min-width: 120px; }
        .events { max-height: 400px; overflow-y: auto; }
        .event { padding: 8px; margin: 5px 0; border-left: 4px solid #ccc; background: #f9f9f9; }
        .event.info { border-left-color: #2196F3; }
        .event.warning { border-left-color: #FF9800; }
        .event.error { border-left-color: #F44336; }
        .event.critical { border-left-color: #D32F2F; }
        button { padding: 10px 15px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-primary { background: #2196F3; color: white; }
        .btn-success { background: #4CAF50; color: white; }
        .btn-warning { background: #FF9800; color: white; }
        .config-rules { background: #f5f5f5; padding: 10px; border-radius: 5px; }
        .rule { margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🖥️ DataBao Monitor Dashboard</h1>
        <p>集中监控服务管理界面</p>
    </div>

    <div class="section">
        <h2>📊 实时统计</h2>
        <div class="stats" id="stats">
            <div class="stat-box">
                <div><strong>总事件数</strong></div>
                <div id="total-events">加载中...</div>
            </div>
            <div class="stat-box">
                <div><strong>成功发送</strong></div>
                <div id="success-sends">加载中...</div>
            </div>
            <div class="stat-box">
                <div><strong>发送失败</strong></div>
                <div id="failed-sends">加载中...</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>⚙️ 配置管理</h2>
        <div>
            <button class="btn-primary" onclick="reloadConfig()">重新加载配置</button>
            <button class="btn-success" onclick="sendTestEvent()">发送测试事件</button>
        </div>
        <div class="config-rules" id="config-rules">
            <strong>路由规则配置:</strong>
            <div id="rules-list">加载中...</div>
        </div>
    </div>

    <div class="section">
        <h2>📋 最近事件</h2>
        <div>
            <button class="btn-primary" onclick="refreshEvents()">刷新事件</button>
            <select id="level-filter" onchange="refreshEvents()">
                <option value="">所有级别</option>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="error">Error</option>
                <option value="critical">Critical</option>
            </select>
        </div>
        <div class="events" id="events">
            <div>加载中...</div>
        </div>
    </div>

    <script>
        // 加载统计信息
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                if (data.success) {
                    document.getElementById('total-events').textContent = data.stats.total_events;
                    document.getElementById('success-sends').textContent = data.stats.webhook_send_success;
                    document.getElementById('failed-sends').textContent = data.stats.webhook_send_failure;
                }
            } catch (e) {
                console.error('加载统计失败:', e);
            }
        }

        // 加载配置信息
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                if (data.success) {
                    const rulesHtml = data.config.route_rules.map(rule => 
                        `<div class="rule">
                            <strong>${rule.name}</strong> 
                            ${rule.enabled ? '✅' : '❌'}
                            <br>服务: ${rule.service || '全部'} | 
                            级别: ${rule.levels.join(', ') || '全部'} | 
                            类型: ${rule.event_types.join(', ') || '全部'}
                        </div>`
                    ).join('');
                    document.getElementById('rules-list').innerHTML = rulesHtml;
                }
            } catch (e) {
                console.error('加载配置失败:', e);
            }
        }

        // 加载最近事件
        async function loadEvents() {
            const levelFilter = document.getElementById('level-filter').value;
            const url = `/api/events?limit=20${levelFilter ? '&level=' + levelFilter : ''}`;
            
            try {
                const response = await fetch(url);
                const data = await response.json();
                if (data.success) {
                    const eventsHtml = data.events.map(event => 
                        `<div class="event ${event.level}">
                            <strong>${event.service}.${event.event_type}</strong> 
                            [${event.level.toUpperCase()}]
                            <br>${event.message}
                            <br><small>${new Date(event.timestamp).toLocaleString()}</small>
                        </div>`
                    ).join('');
                    document.getElementById('events').innerHTML = eventsHtml || '<div>暂无事件</div>';
                }
            } catch (e) {
                console.error('加载事件失败:', e);
                document.getElementById('events').innerHTML = '<div>加载失败</div>';
            }
        }

        // 重新加载配置
        async function reloadConfig() {
            try {
                const response = await fetch('/api/config/reload', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    alert('配置重新加载成功！');
                    loadConfig();
                } else {
                    alert('配置重新加载失败');
                }
            } catch (e) {
                alert('配置重新加载失败: ' + e.message);
            }
        }

        // 发送测试事件
        async function sendTestEvent() {
            try {
                const response = await fetch('/api/test-event', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ service: 'monitor', message: '测试事件 - ' + new Date().toLocaleTimeString() })
                });
                const data = await response.json();
                if (data.success) {
                    alert('测试事件发送成功！');
                    setTimeout(loadEvents, 1000); // 1秒后刷新事件列表
                    loadStats();
                } else {
                    alert('测试事件发送失败');
                }
            } catch (e) {
                alert('测试事件发送失败: ' + e.message);
            }
        }

        // 刷新事件
        function refreshEvents() {
            loadEvents();
        }

        // 页面加载时初始化
        window.onload = function() {
            loadStats();
            loadConfig();
            loadEvents();
            
            // 每30秒自动刷新统计和事件
            setInterval(() => {
                loadStats();
                loadEvents();
            }, 30000);
        };
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)
    
    return app