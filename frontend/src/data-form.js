import { useState } from 'react';
import {
    Box,
    TextField,
    Button,
} from '@mui/material';
import axios from 'axios';

const endpointMapping = {
    'Notion': 'notion',
    'Airtable': 'airtable',
};

export const DataForm = ({ integrationType, credentials }) => {
    const [loadedData, setLoadedData] = useState(null);
    const endpoint = endpointMapping[integrationType];


    const handleLoad = async () => {
        try {
            const response = await axios.post(
                `http://localhost:8000/integrations/${endpoint}/load`,
                {}, // Send empty object instead of credentials
                {
                    headers: {
                        'Content-Type': 'application/json', // Set content type to JSON
                    },
                }
            );
            const data = response.data;
            setLoadedData(data);
        } catch (error) {
            console.error("Error loading data:", error);
            alert(error?.response?.data?.detail || "An error occurred");
        }
    }

    return (
        <Box display='flex' justifyContent='center' alignItems='center' flexDirection='column' width='100%'>
            <Box display='flex' flexDirection='column' width='100%'>
                <TextField
                    label="Loaded Data"
                    value={loadedData || ''}
                    sx={{mt: 2}}
                    InputLabelProps={{ shrink: true }}
                    disabled
                />
                <Button
                    onClick={handleLoad}
                    sx={{mt: 2}}
                    variant='contained'
                >
                    Clear Data
                </Button>
            </Box>
        </Box>
    );
}
