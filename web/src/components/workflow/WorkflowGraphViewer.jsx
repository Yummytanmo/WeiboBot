import React, { useMemo } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    MarkerType,
    BaseEdge,
    getBezierPath,
    EdgeLabelRenderer,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box } from '@mui/material';

// 节点配置（作为 fallback）。当后端未提供结构时使用。
const WORKFLOW_GRAPHS = {
    daily_schedule: {
        nodes: [
            { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', position: { x: 120, y: 40 } },
            { id: 'summarize_trending', label: 'Summarize Trending', icon: '📊', position: { x: 120, y: 170 } },
            { id: 'generate_schedule', label: 'Generate Schedule', icon: '📅', position: { x: 120, y: 300 } },
        ],
        edges: [
            { id: 'ds-1', source: 'fetch_feed', target: 'summarize_trending' },
            { id: 'ds-2', source: 'summarize_trending', target: 'generate_schedule' },
        ],
    },
    post_review: {
        nodes: [
            { id: 'compose', label: 'Compose Draft', icon: '✍️', position: { x: 120, y: 40 } },
            { id: 'review', label: 'Review Draft', icon: '👁️', position: { x: 120, y: 170 } },
            { id: 'post', label: 'Post Weibo', icon: '🚀', position: { x: 120, y: 300 } },
        ],
        edges: [
            { id: 'pr-1', source: 'compose', target: 'review' },
            { id: 'pr-2', source: 'review', target: 'review', label: 'review' },
            { id: 'pr-3', source: 'review', target: 'post', label: 'post' },
        ],
    },
    browse_interaction: {
        nodes: [
            { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', position: { x: 120, y: 40 } },
            { id: 'decide', label: 'Decide Interactions', icon: '🤔', position: { x: 120, y: 170 } },
            { id: 'execute', label: 'Execute Interactions', icon: '💬', position: { x: 120, y: 300 } },
        ],
        edges: [
            { id: 'bi-1', source: 'fetch_feed', target: 'decide' },
            { id: 'bi-2', source: 'decide', target: 'execute' },
        ],
    },
    daily_agent: {
        nodes: [
            { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', position: { x: 80, y: 40 } },
            { id: 'summarize_trending', label: 'Summarize Trending', icon: '📊', position: { x: 80, y: 170 } },
            { id: 'generate_schedule', label: 'Generate Schedule', icon: '📅', position: { x: 80, y: 300 } },
            { id: 'compose_post', label: 'Compose Post', icon: '✍️', position: { x: 300, y: 40 } },
            { id: 'review_post', label: 'Review Post', icon: '👁️', position: { x: 300, y: 170 } },
            { id: 'post_weibo', label: 'Post Weibo', icon: '🚀', position: { x: 300, y: 300 } },
            { id: 'decide_interactions', label: 'Decide Interactions', icon: '🤔', position: { x: 520, y: 170 } },
            { id: 'execute_interactions', label: 'Execute Interactions', icon: '💬', position: { x: 520, y: 300 } },
        ],
        edges: [
            { id: 'da-1', source: 'fetch_feed', target: 'summarize_trending' },
            { id: 'da-2', source: 'summarize_trending', target: 'generate_schedule' },
            { id: 'da-3', source: 'generate_schedule', target: 'compose_post' },
            { id: 'da-4', source: 'compose_post', target: 'review_post' },
            { id: 'da-5', source: 'review_post', target: 'review_post', label: 'review' },
            { id: 'da-6', source: 'review_post', target: 'post_weibo', label: 'post' },
            { id: 'da-7', source: 'post_weibo', target: 'decide_interactions' },
            { id: 'da-8', source: 'decide_interactions', target: 'execute_interactions' },
        ],
    },
};

// 根据状态获取节点颜色
const getNodeColor = (status) => {
    const colors = {
        pending: '#9e9e9e',
        running: '#2196f3',
        completed: '#4caf50',
        failed: '#f44336',
    };
    return colors[status] || colors.pending;
};

// 简易自动布局：按拓扑层级排列，没有位置的节点自动计算。
const autoLayout = (rawNodes, rawEdges) => {
    const nodes = rawNodes.map((n) => ({ ...n }));
    const edges = rawEdges;
    const hasPos = nodes.every((n) => n.position && typeof n.position.x === 'number' && typeof n.position.y === 'number');
    if (hasPos) return nodes;

    const idMap = new Map(nodes.map((n) => [n.id, n]));
    const incoming = new Map(nodes.map((n) => [n.id, 0]));
    edges.forEach((e) => {
        if (e.source === e.target) return;
        if (incoming.has(e.target)) incoming.set(e.target, (incoming.get(e.target) || 0) + 1);
    });
    const levels = new Map();
    const queue = nodes.filter((n) => (incoming.get(n.id) || 0) === 0);
    queue.forEach((n) => levels.set(n.id, 0));
    while (queue.length) {
        const node = queue.shift();
        const level = levels.get(node.id) || 0;
        edges.forEach((e) => {
            if (e.source === node.id && e.source !== e.target) {
                const nextLevel = level + 1;
                if (!levels.has(e.target) || nextLevel > (levels.get(e.target) || 0)) {
                    levels.set(e.target, nextLevel);
                }
                if (incoming.has(e.target)) {
                    incoming.set(e.target, (incoming.get(e.target) || 1) - 1);
                    if (incoming.get(e.target) === 0) {
                        const targetNode = idMap.get(e.target);
                        if (targetNode) queue.push(targetNode);
                    }
                }
            }
        });
    }
    nodes.forEach((n) => {
        if (!levels.has(n.id)) levels.set(n.id, 0);
    });
    const columns = {};
    nodes.forEach((n) => {
        const lvl = levels.get(n.id) || 0;
        if (!columns[lvl]) columns[lvl] = [];
        columns[lvl].push(n.id);
    });
    const spacingX = 240;
    const spacingY = 140;
    Object.entries(columns).forEach(([lvl, ids]) => {
        ids.forEach((id, idx) => {
            const node = idMap.get(id);
            if (node) {
                node.position = {
                    x: Number(lvl) * spacingX,
                    y: idx * spacingY,
                };
            }
        });
    });
    return nodes;
};

const WorkflowGraphViewer = ({ workflowType, currentNode, nodeStatuses = [], graphData }) => {
    const graphConfig = graphData || WORKFLOW_GRAPHS[workflowType] || WORKFLOW_GRAPHS.daily_agent;
    const normalizedNodes = useMemo(() => {
        const nodes = (graphConfig.nodes || []).map((n, idx) => ({
            id: n.id || `n-${idx}`,
            label: n.label || (n.id || '').replace(/_/g, ' ') || `Node ${idx + 1}`,
            icon: n.icon,
            position: n.position,
        }));
        return autoLayout(nodes, graphConfig.edges || []);
    }, [graphConfig]);

    const SelfLoopEdge = ({ id, sourceX, sourceY, markerEnd, style, data }) => {
        const offset = 60;
        const targetX = sourceX + offset;
        const targetY = sourceY - offset;
        const [path, labelX, labelY] = getBezierPath({
            sourceX,
            sourceY,
            sourcePosition: 'right',
            targetX,
            targetY,
            targetPosition: 'bottom',
        });

        return (
            <>
                <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
                {data?.label && (
                    <EdgeLabelRenderer>
                        <div
                            style={{
                                position: 'absolute',
                                transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
                                background: 'rgba(15, 23, 42, 0.9)',
                                color: '#cbd5e1',
                                fontSize: 10,
                                padding: '2px 6px',
                                borderRadius: 8,
                                border: '1px solid rgba(255,255,255,0.08)',
                                pointerEvents: 'none',
                            }}
                        >
                            {data.label}
                        </div>
                    </EdgeLabelRenderer>
                )}
            </>
        );
    };

    // 转换为ReactFlow格式
    const nodes = useMemo(() => {
        return normalizedNodes.map((node) => {
            const nodeStatus = nodeStatuses.find((ns) => ns.id === node.id);
            const status = nodeStatus?.status || 'pending';
            const isActive = currentNode === node.id;
            const pos = node.position || {};
            const statusColor = getNodeColor(status);

            return {
                id: node.id,
                type: 'default',
                position: {
                    x: pos.x ?? 0,
                    y: pos.y ?? 0,
                },
                data: {
                    label: (
                        <Box sx={{ textAlign: 'center' }}>
                            {node.icon && <div style={{ fontSize: '1.5em', marginBottom: '4px' }}>{node.icon}</div>}
                            <div style={{ fontSize: '0.9em', fontWeight: 'bold' }}>{node.label}</div>
                            {nodeStatus?.duration && (
                                <div style={{ fontSize: '0.7em', color: '#666' }}>
                                    {nodeStatus.duration.toFixed(1)}s
                                </div>
                            )}
                        </Box>
                    ),
                },
                style: {
                    background: isActive ? 'linear-gradient(135deg, #2f80ed, #56ccf2)' : statusColor,
                    color: '#f5f7fb',
                    border: isActive ? '2px solid rgba(255,255,255,0.6)' : `1px solid ${statusColor}`,
                    borderRadius: '14px',
                    padding: '12px',
                    minWidth: '140px',
                    boxShadow: isActive
                        ? '0 10px 26px rgba(47, 128, 237, 0.35)'
                        : '0 8px 18px rgba(0,0,0,0.35)',
                },
            };
        });
    }, [normalizedNodes, currentNode, nodeStatuses]);

    const edges = useMemo(() => {
        return (graphConfig.edges || []).map((edge, idx) => {
            const source = edge.source;
            const target = edge.target;
            const isLoop = source === target;
            return {
                id: edge.id || `e-${idx}`,
                source,
                target,
                type: isLoop ? 'self-loop' : 'smoothstep',
                data: { label: edge.label },
                animated: currentNode === source,
                markerEnd: { type: MarkerType.ArrowClosed, color: '#5c6c84' },
                style: {
                    stroke: currentNode === source ? '#56ccf2' : '#5c6c84',
                    strokeWidth: 2.2,
                },
                label: edge.label,
                labelStyle: { fill: '#9aa8c0', fontSize: 10 },
            };
        });
    }, [graphConfig, currentNode]);

    return (
        <Box sx={{ width: '100%', height: '100%', bgcolor: '#0e1118' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                attributionPosition="bottom-right"
                edgeTypes={{ 'self-loop': SelfLoopEdge }}
            >
                <Background color="#1f2430" variant="dots" gap={14} size={1.5} />
                <Controls />
                <MiniMap
                    nodeColor={(n) => n.style.background}
                    maskColor="rgba(0, 0, 0, 0.3)"
                />
            </ReactFlow>
        </Box>
    );
};

export default WorkflowGraphViewer;
