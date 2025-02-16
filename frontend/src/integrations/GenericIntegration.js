import { useState, useEffect } from 'react';
import { Box, Button, CircularProgress } from '@mui/material';
import axios from 'axios';

export const GenericIntegration = ({ 
    user, 
    org, 
    integrationParams, 
    setIntegrationParams, 
    integrationType 
}) => {
    const [isConnected, setIsConnected] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);

    const endpoints = {
        authorize: `http://localhost:8000/integrations/${integrationType.toLowerCase()}/authorize`,
        credentials: `http://localhost:8000/integrations/${integrationType.toLowerCase()}/credentials`,
    };

    // Handle OAuth connection
    const handleConnectClick = async () => {
        try {
            setIsConnecting(true);
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);

            // Start OAuth flow
            const response = await axios.post(endpoints.authorize, formData);
            const authWindow = window.open(response.data, `${integrationType} Auth`, 'width=600,height=600');

            // Poll for window closure
            const poll = setInterval(() => {
                if (authWindow.closed) {
                    clearInterval(poll);
                    handleAuthComplete();
                }
            }, 200);
        } catch (error) {
            setIsConnecting(false);
            alert(error.response?.data?.detail || `Failed to connect to ${integrationType}`);
        }
    };

    // Handle OAuth completion
    const handleAuthComplete = async () => {
        try {
            const formData = new FormData();
            formData.append('user_id', user);
            formData.append('org_id', org);

            // Retrieve credentials
            const { data } = await axios.post(endpoints.credentials, formData);

            // Update integration params
            setIntegrationParams({
                ...integrationParams,
                credentials: data,
                type: integrationType,
            });
            setIsConnected(true);
        } catch (error) {
            alert(error.response?.data?.detail || `Failed to retrieve ${integrationType} credentials`);
        } finally {
            setIsConnecting(false);
        }
    };

    // Check if already connected
    useEffect(() => {
        setIsConnected(integrationParams?.type === integrationType && !!integrationParams?.credentials);
    }, [integrationParams, integrationType]);

    return (
        <Box sx={{ mt: 2 }}>
            <Button
                variant="contained"
                onClick={handleConnectClick}
                disabled={isConnecting || isConnected}
                color={isConnected ? 'success' : 'primary'}
                sx={{
                    pointerEvents: isConnected ? 'none' : 'auto',
                    cursor: isConnected ? 'default' : 'pointer',
                }}
            >
                {isConnected ? `${integrationType} Connected` : 
                 isConnecting ? <CircularProgress size={20} /> : `Connect to ${integrationType}`}
            </Button>
        </Box>
    );
};