import fs from 'node:fs/promises';import path from 'node:path';import {pathToFileURL,fileURLToPath} from 'node:url';
const O=path.dirname(fileURLToPath(import.meta.url)),W=path.resolve(O,'../..');
const SK='C:/Users/xuan1/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations';
process.env.RUNTIME_NODE_MODULES='C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(path.join(SK,'container_tools/artifact_tool_utils.mjs')));
const [input,output,count,mode]=process.argv.slice(2);const isBar=mode==='bar';
await fs.mkdir(path.join(O,'output'),{recursive:true});
await finalizePresentation({workspaceDir:W,candidatePath:path.join(O,input),finalPath:path.join(O,'output',output),pythonExecutable:'C:/Users/xuan1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',integrityValidatorPath:path.join(SK,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SK,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',input.startsWith('figure1')?'17526000,13144500':'12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:Number(count),requiredNativeChartOwnerSlides:isBar?[1]:Number(count)===7?[2,3,4,6]:[],materializeLiteralChartWorkbooks:isBar,fontPolicy:{basis:'user_request',families:['Times New Roman']},verifyArtifactToolImport:true,receiptPath:path.join(O,output+'.validation.json')});console.log('Validated '+output);
