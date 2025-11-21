import React, { useState, useCallback, useRef } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    addEdge,
    useNodesState,
    useEdgesState,
    MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Box, Button, AppBar, Toolbar, Typography } from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import FolderOpenIcon from '@mui/icons-material/FolderOpen';

import NodeLibrary from '../components/workflow/NodeLibrary';
import PropertiesPanel from '../components/workflow/PropertiesPanel';
import CustomNode from '../components/workflow/CustomNode';

const nodeTypes = {
    custom: CustomNode,
};

const WorkflowBuilder = () => {
    const reactFlowWrapper = useRef(null);
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [selectedNode, setSelectedNode] = useState(null);
    const [reactFlowInstance, setReactFlowInstance] = useState(null);

    const onConnect = useCallback(
        (params) => setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
        []
    );

    const onNodeClick = useCallback((event, node) => {
        setSelectedNode(node);
    }, []);

    const onDragOver = useCallback((event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event) => {
            event.preventDefault();

            const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
            const nodeData = JSON.parse(event.dataTransfer.getData('application/reactflow'));

            const position = reactFlowInstance.project({
                x: event.clientX - reactFlowBounds.left,
                y: event.clientY - reactFlowBounds.top,
            });

            const newNode = {
                id: `${nodeData.id}_${Date.now()}`,
                type: 'custom',
                position,
                data: { ...nodeData },
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance]
    );

    const saveWorkflow = async () => {
        const workflow = {
            nodes,
            edges,
            name: 'Custom Workflow',
            timestamp: new Date().toISOString(),
        };
        console.log('Saving workflow:', workflow);
        // TODO: 实现保存API调用
        alert(`Workflow保存成功！\n节点数: ${nodes.length}\n连接数: ${edges.length}`);
    };

    const loadWorkflow = () => {
        // TODO: 实现加载功能
        console.log('Loading workflow...');
        alert('加载功能待实现');
    };

    const executeWorkflow = async () => {
        if (nodes.length === 0) {
            alert('请先添加节点！');
            return;
        }
        console.log('Executing workflow with nodes:', nodes.length, 'edges:', edges.length);
        // TODO: 实现执行API调用
        alert(`Workflow执行中...\n节点数: ${nodes.length}\n连接数: ${edges.length}`);
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        🔧 Workflow Builder
                    </Typography>
                    <Button color="inherit" startIcon={<FolderOpenIcon />} onClick={loadWorkflow} sx={{ mr: 1 }}>
                        Load
                    </Button>
                    <Button color="inherit" startIcon={<SaveIcon />} onClick={saveWorkflow} sx={{ mr: 1 }}>
                        Save
                    </Button>
                    <Button color="inherit" startIcon={<PlayArrowIcon />} onClick={executeWorkflow} variant="outlined">
                        Execute
                    </Button>
                </Toolbar>
            </AppBar>

            <Box sx={{ display: 'flex', flexGrow: 1 }}>
                <NodeLibrary />

                <Box ref={reactFlowWrapper} sx={{ flexGrow: 1, bgcolor: 'grey.50' }}>
                    <ReactFlow
                        nodes={nodes}
                        edges={edges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        onNodeClick={onNodeClick}
                        onInit={setReactFlowInstance}
                        onDrop={onDrop}
                        onDragOver={onDragOver}
                        nodeTypes={nodeTypes}
                        fitView
                    >
                        <Background />
                        <Controls />
                        <MiniMap />
                    </ReactFlow>
                </Box>

                <PropertiesPanel node={selectedNode} />
            </Box>
        </Box>
    );
};

export default WorkflowBuilder;
