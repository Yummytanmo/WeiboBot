import React, { useMemo } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box } from '@mui/material';

// 节点配置（定义每个workflow的节点和边）
const WORKFLOW_GRAPHS = {
    daily_schedule: {
        nodes: [
            { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', position: { x: 100, y: 50 } },
            { id: 'summarize_trending', label: 'Summarize Trending', icon: '📊', position: { x: 100, y: 150 } },
            { id: 'generate_schedule', label: 'Generate Schedule', icon: '📅', position: { x: 100, y: 250 } },
        ],
        edges: [
            { id: 'e1', source: 'fetch_feed', target: 'summarize_trending' },
            { id: 'e2', source: 'summarize_trending', target: 'generate_schedule' },
        ],
    },
    post_review: {
        nodes: [
            { id: 'compose_post', label: 'Compose Post', icon: '✍️', position: { x: 100, y: 50 } },
            { id: 'review_post', label: 'Review Post', icon: '👁️', position: { x: 100, y: 150 } },
            { id: 'post_weibo', label: 'Post Weibo', icon: '🚀', position: { x: 100, y: 250 } },
        ],
        edges: [
            { id: 'e1', source: 'compose_post', target: 'review_post' },
            { id: 'e2', source: 'review_post', target: 'review_post', label: 'review' },
            { id: 'e3', source: 'review_post', target: 'post_weibo', label: 'post' },
        ],
    },
    browse_interaction: {
        nodes: [
            { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', position: { x: 100, y: 50 } },
            { id: 'decide_interactions', label: 'Decide Interactions', icon: '🤔', position: { x: 100, y: 150 } },
            { id: 'execute_interactions', label: 'Execute Interactions', icon: '💬', position: { x: 100, y: 250 } },
        ],
        edges: [
            { id: 'e1', source: 'fetch_feed', target: 'decide_interactions' },
            { id: 'e2', source: 'decide_interactions', target: 'execute_interactions' },
        ],
    },
    daily_agent: {
        nodes: [
            { id: 'fetch_feed', label: 'Fetch Feed', icon: '📥', position: { x: 50, y: 50 } },
            { id: 'summarize_trending', label: 'Summarize Trending', icon: '📊', position: { x: 50, y: 150 } },
            { id: 'generate_schedule', label: 'Generate Schedule', icon: '📅', position: { x: 50, y: 250 } },
            { id: 'compose_post', label: 'Compose Post', icon: '✍️', position: { x: 250, y: 50 } },
            { id: 'review_post', label: 'Review Post', icon: '👁️', position: { x: 250, y: 150 } },
            { id: 'post_weibo', label: 'Post Weibo', icon: '🚀', position: { x: 250, y: 250 } },
            { id: 'decide_interactions', label: 'Decide Interactions', icon: '🤔', position: { x: 450, y: 150 } },
            { id: 'execute_interactions', label: 'Execute Interactions', icon: '💬', position: { x: 450, y: 250 } },
        ],
        edges: [
            { id: 'e1', source: 'fetch_feed', target: 'summarize_trending' },
            { id: 'e2', source: 'summarize_trending', target: 'generate_schedule' },
            { id: 'e3', source: 'generate_schedule', target: 'compose_post' },
            { id: 'e4', source: 'compose_post', target: 'review_post' },
            { id: 'e5', source: 'review_post', target: 'review_post', label: 'review' },
            { id: 'e6', source: 'review_post', target: 'post_weibo', label: 'post' },
            { id: 'e7', source: 'post_weibo', target: 'decide_interactions' },
            { id: 'e8', source: 'decide_interactions', target: 'execute_interactions' },
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

const WorkflowGraphViewer = ({ workflowType, currentNode, nodeStatuses = [] }) => {
    const graphConfig = WORKFLOW_GRAPHS[workflowType] || WORKFLOW_GRAPHS.daily_agent;

    // 转换为ReactFlow格式
    const nodes = useMemo(() => {
        return graphConfig.nodes.map((node) => {
            const nodeStatus = nodeStatuses.find((ns) => ns.id === node.id);
            const status = nodeStatus?.status || 'pending';
            const isActive = currentNode === node.id;

            return {
                id: node.id,
                type: 'default',
                position: node.position,
                data: {
                    label: (
                        <Box sx={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '1.5em', marginBottom: '4px' }}>{node.icon}</div>
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
                    background: getNodeColor(status),
                    color: '#fff',
                    border: isActive ? '3px solid #ff9800' : '2px solid #666',
                    borderRadius: '8px',
                    padding: '12px',
                    minWidth: '140px',
                    boxShadow: isActive ? '0 0 20px rgba(255, 152, 0, 0.5)' : '0 2px 4px rgba(0,0,0,0.2)',
                },
            };
        });
    }, [graphConfig, currentNode, nodeStatuses]);

    const edges = useMemo(() => {
        return graphConfig.edges.map((edge) => ({
            ...edge,
            type: 'smoothstep',
            animated: currentNode === edge.source,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: {
                stroke: '#666',
                strokeWidth: 2,
            },
            label: edge.label,
            labelStyle: { fill: '#666', fontSize: 10 },
        }));
    }, [graphConfig, currentNode]);

    return (
        <Box sx={{ width: '100%', height: '100%', bgcolor: 'grey.50' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                attributionPosition="bottom-right"
            >
                <Background />
                <Controls />
                <MiniMap
                    nodeColor={(n) => n.style.background}
                    maskColor="rgba(0, 0, 0, 0.1)"
                />
            </ReactFlow>
        </Box>
    );
};

export default WorkflowGraphViewer;
