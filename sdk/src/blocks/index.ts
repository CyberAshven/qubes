/**
 * Blocks module — Block class, genesis/memory factories, chain state.
 *
 * ```ts
 * import {
 *   QubeBlock,
 *   createGenesisBlock,
 *   createMessageBlock,
 *   createDefaultChainState,
 * } from '@qubesai/sdk/blocks';
 * ```
 *
 * @module blocks
 */

// Block class
export { QubeBlock } from './block.js';

// Genesis block factory
export { createGenesisBlock, type CreateGenesisBlockParams } from './genesis.js';

// Memory block factories (all 10 types)
export {
  // Factories
  createThoughtBlock,
  createActionBlock,
  createObservationBlock,
  createMessageBlock,
  createDecisionBlock,
  createMemoryAnchorBlock,
  createCollaborativeMemoryBlock,
  createSummaryBlock,
  createGameBlock,
  createLearningBlock,
  // Constants
  VALID_LEARNING_TYPES,
  // Param interfaces
  type CommonBlockParams,
  type CreateThoughtBlockParams,
  type CreateActionBlockParams,
  type CreateObservationBlockParams,
  type CreateMessageBlockParams,
  type CreateDecisionBlockParams,
  type CreateMemoryAnchorBlockParams,
  type CreateCollaborativeMemoryBlockParams,
  type CreateSummaryBlockParams,
  type CreateGameBlockParams,
  type CreateLearningBlockParams,
} from './memory.js';

// Chain state factory
export { createDefaultChainState } from './chain-state.js';
