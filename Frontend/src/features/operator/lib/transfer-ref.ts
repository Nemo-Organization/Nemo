// "7c1e4b2a-...-5b0f2c3da90b" -> "TRF 7c1e...a90b"
export const formatTransferRef = (transferId: string) =>
  `TRF ${transferId.slice(0, 4)}...${transferId.slice(-4)}`;
